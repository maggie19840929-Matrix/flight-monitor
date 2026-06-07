"""
去哪儿 (Qunar) searcher.
Codex: implement _search() using the approach below.

Approach (mobile JSON API — no official open API available):
  GET https://m.qunar.com/api/flight/searchDomesticRT
  Params:
    fromCity=PEK, toCity=SHA, fromDate=2026-07-15, retDate=2026-07-22
    (oneway: use /searchDomesticOW and omit retDate)

  Response JSON path: data.flightList[].priceList[]
  Key fields:
    flightNo, airlineCode, depDateTime, arrDateTime, price, seat, deepLink
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import requests

from ..models import FlightLeg, RoundTripBundle, TripType, WatchConfig
from .base import BaseSearcher


class QunarSearcher(BaseSearcher):
    source_name = "qunar"

    _BASE_OW = "https://m.qunar.com/api/flight/searchDomesticOW"
    _BASE_RT = "https://m.qunar.com/api/flight/searchDomesticRT"

    def __init__(self, cfg: dict, proxy: dict | None):
        super().__init__(cfg, proxy)
        self._session = requests.Session()

    def _search(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        # TODO: build params dict, call _BASE_OW or _BASE_RT based on trip_type
        # TODO: call _parse_response on successful JSON
        params = {
            "fromCity": watch.outbound_origin,
            "toCity": watch.outbound_destination,
            "fromDate": watch.outbound_date.isoformat(),
            "adult": watch.passengers,
            "child": 0,
            "infant": 0,
        }
        url = self._BASE_OW
        if watch.trip_type == TripType.ROUNDTRIP:
            url = self._BASE_RT
            params["retDate"] = watch.return_date.isoformat()

        resp = self._session.get(
            url,
            params=params,
            proxies=self.proxy,
            timeout=self.cfg.get("timeout", 20),
        )
        resp.raise_for_status()
        return self._parse_response(resp.json(), watch)

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        # TODO: iterate raw["data"]["flightList"] → FlightLeg objects
        def _get(*dicts: dict, names: tuple[str, ...]) -> Any:
            for data in dicts:
                for name in names:
                    value = data.get(name)
                    if value not in (None, ""):
                        return value
            return None

        def _parse_dt(value: Any, travel_date) -> datetime:
            if isinstance(value, datetime):
                return value
            text = str(value)
            if "T" in text or "-" in text:
                return datetime.fromisoformat(text.replace("Z", "+00:00"))
            if ":" in text:
                parsed_time = datetime.strptime(text, "%H:%M").time()
            else:
                parsed_time = datetime.strptime(text.zfill(4), "%H%M").time()
            return datetime.combine(travel_date, parsed_time)

        def _seats_left(*dicts: dict) -> int:
            value = _get(*dicts, names=("seatsLeft", "seat", "seatCount", "quantity"))
            try:
                return int(value) if value is not None else -1
            except (TypeError, ValueError):
                return -1

        def _leg(parent: dict, price_item: dict, travel_date, origin: str, destination: str) -> FlightLeg | None:
            price = _get(price_item, parent, names=("price", "minPrice", "barePrice"))
            flight_no = _get(price_item, parent, names=("flightNo", "flightNO"))
            dep_value = _get(price_item, parent, names=("depDateTime", "depTime", "dptTime"))
            arr_value = _get(price_item, parent, names=("arrDateTime", "arrTime", "arrtTime"))
            if price is None or not flight_no or dep_value is None or arr_value is None:
                return None
            dep_time = _parse_dt(dep_value, travel_date)
            arr_time = _parse_dt(arr_value, travel_date)
            if arr_time <= dep_time:
                arr_time += timedelta(days=1)
            return FlightLeg(
                origin=_get(price_item, parent, names=("depAirportCode", "fromAirportCode")) or origin,
                destination=_get(price_item, parent, names=("arrAirportCode", "toAirportCode")) or destination,
                date=dep_time.date(),
                flight_no=str(flight_no),
                airline=_get(price_item, parent, names=("airlineCode", "carrierCode")) or str(flight_no)[:2],
                departure_time=dep_time,
                arrival_time=arr_time,
                duration_minutes=int((arr_time - dep_time).total_seconds() // 60),
                cabin=watch.cabin,
                price=float(price),
                seats_left=_seats_left(price_item, parent),
                source=self.source_name,
                booking_url=_get(price_item, parent, names=("deepLink", "bookingUrl", "url")) or "",
            )

        results: list[FlightLeg | RoundTripBundle] = []
        data = raw.get("data", {}) if isinstance(raw, dict) else {}
        for item in data.get("flightList", []):
            price_list = item.get("priceList") or [item]
            for price_item in price_list:
                if watch.trip_type == TripType.ROUNDTRIP:
                    outbound_data = price_item.get("outbound") or price_item.get("depFlight") or price_item.get("goFlight")
                    inbound_data = price_item.get("inbound") or price_item.get("retFlight") or price_item.get("backFlight")
                    if outbound_data and inbound_data:
                        outbound = _leg(item, outbound_data, watch.outbound_date, watch.outbound_origin, watch.outbound_destination)
                        inbound = _leg(item, inbound_data, watch.return_date, watch.return_origin, watch.return_destination)
                        if outbound and inbound:
                            total_price = float(price_item.get("price", outbound.price + inbound.price))
                            results.append(
                                RoundTripBundle(
                                    outbound=outbound,
                                    inbound=inbound,
                                    total_price=total_price,
                                    bundle_url=price_item.get("deepLink") or outbound.booking_url,
                                )
                            )
                            continue

                leg = _leg(item, price_item, watch.outbound_date, watch.outbound_origin, watch.outbound_destination)
                if leg:
                    results.append(leg)
        return results
