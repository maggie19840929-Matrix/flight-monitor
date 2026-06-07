"""
飞猪 (Fliggy / trip.taobao.com) searcher.

Mobile JSON endpoint (reverse-engineered):
  GET https://m.fliggy.com/flightsearch/search.do
  Params:
    depCity=PEK, arrCity=SHA, depDate=2026-07-15, tripType=OW|RT
    retDate=2026-07-22 (roundtrip only), adult=1

  Response path: data.flightList[].priceList[]
  Key fields: flightNo, airlineCode, depTime, arrTime, price, deepLink

Booking URL pattern:
  https://www.fliggy.com/flights/domestic/{origin}-{destination}/{date}/
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import requests

from ..models import Cabin, FlightLeg, RoundTripBundle, TripType, WatchConfig
from .base import BaseSearcher

_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 AliApp(Trip/3.0)",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36 AliApp(Trip/3.0)",
]

_BASE_URL = "https://m.fliggy.com/flightsearch/search.do"


class FliggySearcher(BaseSearcher):
    source_name = "fliggy"

    def __init__(self, cfg: dict, proxy: dict | None):
        super().__init__(cfg, proxy)
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": _USER_AGENTS[0],
            "Referer": "https://m.fliggy.com/",
            "Accept": "application/json, text/plain, */*",
        })

    def _search(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        import random
        self._session.headers["User-Agent"] = random.choice(_USER_AGENTS)

        params: dict[str, Any] = {
            "depCity": watch.outbound_origin,
            "arrCity": watch.outbound_destination,
            "depDate": watch.outbound_date.isoformat(),
            "tripType": "RT" if watch.trip_type == TripType.ROUNDTRIP else "OW",
            "adult": watch.passengers,
            "child": 0,
            "infant": 0,
        }
        if watch.trip_type == TripType.ROUNDTRIP and watch.return_date:
            params["retDate"] = watch.return_date.isoformat()

        resp = self._session.get(
            _BASE_URL,
            params=params,
            proxies=self.proxy,
            timeout=self.cfg.get("timeout", 20),
        )
        if resp.status_code == 429:
            import time
            time.sleep(60)
            resp = self._session.get(_BASE_URL, params=params, proxies=self.proxy, timeout=20)
        resp.raise_for_status()
        return self._parse_response(resp.json(), watch)

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        def _get(data: dict, *names: str) -> Any:
            for name in names:
                v = data.get(name)
                if v not in (None, ""):
                    return v
            return None

        def _parse_dt(value: Any, base_date) -> datetime:
            if isinstance(value, datetime):
                return value
            text = str(value)
            if "T" in text or ("-" in text and len(text) > 10):
                return datetime.fromisoformat(text.replace("Z", "+00:00"))
            if ":" in text:
                t = datetime.strptime(text, "%H:%M").time()
            else:
                t = datetime.strptime(text.zfill(4), "%H%M").time()
            return datetime.combine(base_date, t)

        def _booking_url(flight_no: str, origin: str, dest: str, dep_date) -> str:
            base = f"https://www.fliggy.com/flights/domestic/{origin}-{dest}/{dep_date.isoformat()}/"
            return f"{base}?flightNo={flight_no}"

        def _make_leg(item: dict, price_item: dict, travel_date, origin: str, dest: str) -> FlightLeg | None:
            flight_no = _get(item, "flightNo", "flightNO")
            dep_val = _get(item, price_item, "depTime", "depDateTime", "departureTime")
            arr_val = _get(item, price_item, "arrTime", "arrDateTime", "arrivalTime")
            price = _get(price_item, item, "price", "salePrice", "minPrice")
            if not flight_no or dep_val is None or arr_val is None or price is None:
                return None
            try:
                dep_time = _parse_dt(dep_val, travel_date)
                arr_time = _parse_dt(arr_val, travel_date)
                price_val = float(price)
            except (TypeError, ValueError):
                return None
            if arr_time <= dep_time:
                arr_time += timedelta(days=1)
            booking = _get(price_item, item, "deepLink", "bookingUrl", "url") or _booking_url(
                flight_no,
                _get(item, "depAirportCode", "fromCity") or origin,
                _get(item, "arrAirportCode", "toCity") or dest,
                dep_time.date(),
            )
            return FlightLeg(
                origin=_get(item, "depAirportCode", "fromCity") or origin,
                destination=_get(item, "arrAirportCode", "toCity") or dest,
                date=dep_time.date(),
                flight_no=str(flight_no),
                airline=_get(item, "airlineCode", "carrierCode") or str(flight_no)[:2],
                departure_time=dep_time,
                arrival_time=arr_time,
                duration_minutes=int((arr_time - dep_time).total_seconds() // 60),
                cabin=watch.cabin,
                price=price_val,
                seats_left=int(_get(price_item, item, "seatsLeft", "seatCount") or -1),
                source=self.source_name,
                booking_url=booking,
            )

        results: list[FlightLeg | RoundTripBundle] = []
        data = raw.get("data", {}) if isinstance(raw, dict) else {}

        for item in data.get("flightList", []):
            price_list = item.get("priceList") or [item]
            for price_item in price_list:
                if watch.trip_type == TripType.ROUNDTRIP:
                    out_data = price_item.get("outbound") or price_item.get("goFlight") or {}
                    in_data = price_item.get("inbound") or price_item.get("backFlight") or {}
                    if out_data and in_data:
                        outbound = _make_leg(out_data, price_item, watch.outbound_date,
                                             watch.outbound_origin, watch.outbound_destination)
                        inbound = _make_leg(in_data, price_item, watch.return_date,
                                            watch.return_origin or watch.outbound_destination,
                                            watch.return_destination or watch.outbound_origin)
                        if outbound and inbound:
                            total = float(price_item.get("price", outbound.price + inbound.price))
                            results.append(RoundTripBundle(
                                outbound=outbound,
                                inbound=inbound,
                                total_price=total,
                                bundle_url=price_item.get("deepLink") or outbound.booking_url,
                            ))
                            continue
                leg = _make_leg(item, price_item, watch.outbound_date,
                                watch.outbound_origin, watch.outbound_destination)
                if leg:
                    results.append(leg)
        return results
