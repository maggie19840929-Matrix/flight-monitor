"""
携程 (Ctrip / Trip.com) searcher.
Codex: implement _search() using the approach below.

Approach:
  1. If cfg["api_key"] is set → use Trip.com Open API (preferred, stable):
       POST https://openapi.trip.com/flight/search
       Doc: https://hyz.trip.com/doc/flight

  2. Else → scrape the mobile JSON API (reverse-engineered endpoint):
       POST https://m.ctrip.com/restapi/soa2/15757/json/searchFlights
       Headers: Content-Type: application/json, Accept: */*
       Body: see CODEX_TASKS.md §Ctrip for the exact JSON schema

Session management:
  - Maintain a requests.Session() with cookies; reuse across calls.
  - Rotate User-Agent from a short list (see _USER_AGENTS below).
  - On HTTP 429 → sleep 60 s and retry once.
"""
from __future__ import annotations

from datetime import datetime
import time
from typing import Any
import urllib.parse

import requests

from ..models import FlightLeg, RoundTripBundle, TripType, WatchConfig
from .base import BaseSearcher

_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.43",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]


class CtripSearcher(BaseSearcher):
    source_name = "ctrip"

    def __init__(self, cfg: dict, proxy: dict | None):
        super().__init__(cfg, proxy)
        self._session = requests.Session()
        # TODO: initialise session headers

    def _search(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        # TODO: branch on api_key presence → API vs scrape path
        flight_way = "D" if watch.trip_type == TripType.ROUNDTRIP else "S"
        airport_params = [
            {
                "cityType": 0,
                "dcity": watch.outbound_origin,
                "acity": watch.outbound_destination,
                "date": watch.outbound_date.isoformat(),
            }
        ]
        if watch.trip_type == TripType.ROUNDTRIP:
            airport_params.append(
                {
                    "cityType": 0,
                    "dcity": watch.return_origin,
                    "acity": watch.return_destination,
                    "date": watch.return_date.isoformat(),
                }
            )

        payload = {
            "flightWay": flight_way,
            "classType": "ALL",
            "hasChild": False,
            "hasBaby": False,
            "searchIndex": 1,
            "airportParams": airport_params,
        }
        endpoint = (
            "https://openapi.trip.com/flight/search"
            if self.cfg.get("api_key")
            else "https://m.ctrip.com/restapi/soa2/15757/json/searchFlights"
        )
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENTS[0],
        }
        if self.cfg.get("api_key"):
            headers["Authorization"] = self.cfg["api_key"]

        resp = self._session.post(
            endpoint,
            json=payload,
            headers=headers,
            proxies=self.proxy,
            timeout=self.cfg.get("timeout", 20),
        )
        if resp.status_code == 429:
            time.sleep(60)
            resp = self._session.post(
                endpoint,
                json=payload,
                headers=headers,
                proxies=self.proxy,
                timeout=self.cfg.get("timeout", 20),
            )
        resp.raise_for_status()
        return self._parse_response(resp.json(), watch)

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        # TODO: walk raw JSON; map each flight item to FlightLeg
        # booking_url pattern: https://www.ctrip.com/online/clk/toBook.aspx?...
        def _parse_dt(value: str) -> datetime:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))

        def _price_info(segment: dict, item: dict) -> dict:
            prices = segment.get("priceList") or item.get("priceList") or []
            return prices[0] if prices else {}

        def _booking_url(segment: dict, dep_time: datetime) -> str:
            params = {
                "flighttype": "D" if watch.trip_type == TripType.ROUNDTRIP else "S",
                "ddate": dep_time.date().isoformat(),
                "dcity": segment.get("depAirportCode", watch.outbound_origin),
                "acity": segment.get("arrAirportCode", watch.outbound_destination),
                "flightNo": segment.get("flightNo", ""),
                "classType": "Y",
            }
            return "https://www.ctrip.com/online/clk/toBook.aspx?" + urllib.parse.urlencode(params)

        def _seats_left(price_info: dict) -> int:
            for key in ("seatsLeft", "seatCount", "seat", "quantity"):
                value = price_info.get(key)
                if value is not None:
                    try:
                        return int(value)
                    except (TypeError, ValueError):
                        return -1
            return -1

        def _leg(segment: dict, item: dict) -> FlightLeg | None:
            price_info = _price_info(segment, item)
            if not price_info or price_info.get("price") is None:
                return None
            dep_time = _parse_dt(segment["depDateTime"])
            arr_time = _parse_dt(segment["arrDateTime"])
            flight_no = segment["flightNo"]
            booking_url = price_info.get("hyperlink") or _booking_url(segment, dep_time)
            return FlightLeg(
                origin=segment.get("depAirportCode", watch.outbound_origin),
                destination=segment.get("arrAirportCode", watch.outbound_destination),
                date=dep_time.date(),
                flight_no=flight_no,
                airline=segment.get("airlineCode") or flight_no[:2],
                departure_time=dep_time,
                arrival_time=arr_time,
                duration_minutes=int((arr_time - dep_time).total_seconds() // 60),
                cabin=watch.cabin,
                price=float(price_info["price"]),
                seats_left=_seats_left(price_info),
                source=self.source_name,
                booking_url=booking_url,
            )

        results: list[FlightLeg | RoundTripBundle] = []
        data = raw.get("data", {}) if isinstance(raw, dict) else {}
        for item in data.get("flightItineraryList", []):
            segments = item.get("flightSegments", [])
            if watch.trip_type == TripType.ROUNDTRIP and len(segments) >= 2:
                outbound = _leg(segments[0], item)
                inbound = _leg(segments[1], item)
                if outbound and inbound:
                    bundle_url = item.get("hyperlink") or outbound.booking_url
                    results.append(
                        RoundTripBundle(
                            outbound=outbound,
                            inbound=inbound,
                            total_price=float(item.get("totalPrice", outbound.price + inbound.price)),
                            bundle_url=bundle_url,
                        )
                    )
            elif segments:
                leg = _leg(segments[0], item)
                if leg:
                    results.append(leg)
        return results
