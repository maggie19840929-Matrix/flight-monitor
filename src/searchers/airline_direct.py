"""
直连航司官网 searcher (Playwright headless scraping).
Codex: implement per-airline scrapers as subclasses of AirlineDirectSearcher.

Why Playwright (not requests):
  Airline sites are SPA / JS-rendered.  Playwright is already in requirements.txt.

Per-airline URL patterns:
  CA (国航): https://www.airchina.com.cn/reserve/initSearchAction.do
             POST form: depDate, arrDate, dCity, aCity, travelType, cabin
  MU (东航): https://www.ceair.com/booking/flight-search_V4.html#/...
             GET URL hash params; JSON loaded via XHR /ceas/pc/search
  CZ (南航): https://www.csair.com/cn/booking/flight_searching.shtml
             POST /booking/searchFlight.do (JSON body)

Implementation pattern for each airline:
  1. Launch Playwright browser (chromium, headless=True)
  2. Intercept XHR responses matching the JSON endpoint (page.route / page.on("response"))
  3. Parse intercepted JSON → FlightLeg objects (cheaper than DOM scraping)
  4. Close browser
"""
from __future__ import annotations

import abc
from datetime import datetime, timedelta
import logging
from typing import Any

from ..models import FlightLeg, RoundTripBundle, WatchConfig
from .base import BaseSearcher

logger = logging.getLogger(__name__)


def _parse_airline_json(raw: Any, watch: WatchConfig, carrier_code: str) -> list[FlightLeg | RoundTripBundle]:
    def _walk(obj: Any):
        if isinstance(obj, dict):
            yield obj
            for value in obj.values():
                yield from _walk(value)
        elif isinstance(obj, list):
            for value in obj:
                yield from _walk(value)

    def _get(data: dict, names: tuple[str, ...]) -> Any:
        for name in names:
            value = data.get(name)
            if value not in (None, ""):
                return value
        return None

    def _parse_dt(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        text = str(value)
        if "T" in text or "-" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        parsed = datetime.strptime(text if ":" in text else text.zfill(4), "%H:%M" if ":" in text else "%H%M")
        return datetime.combine(watch.outbound_date, parsed.time())

    def _seats_left(data: dict) -> int:
        value = _get(data, ("seatsLeft", "seatCount", "seat", "remainSeat", "quantity"))
        try:
            return int(value) if value is not None else -1
        except (TypeError, ValueError):
            return -1

    seen: set[tuple[str, str, str, float]] = set()
    results: list[FlightLeg | RoundTripBundle] = []
    for item in _walk(raw):
        flight_no = _get(item, ("flightNo", "flightNO", "flight_no", "flightNumber", "flightNum", "airLineNo"))
        dep_value = _get(item, ("depDateTime", "depTime", "departureTime", "takeoffTime", "dptTime", "deptTime"))
        arr_value = _get(item, ("arrDateTime", "arrTime", "arrivalTime", "landingTime", "arrvTime"))
        price = _get(item, ("price", "ticketPrice", "salePrice", "fare", "minPrice", "cabinPrice", "adultPrice", "amount"))
        if not flight_no or dep_value is None or arr_value is None or price is None:
            continue
        try:
            dep_time = _parse_dt(dep_value)
            arr_time = _parse_dt(arr_value)
            price_value = float(price)
        except (TypeError, ValueError):
            continue
        if arr_time <= dep_time:
            arr_time += timedelta(days=1)

        origin = _get(item, ("depAirportCode", "dptAirportCode", "depAirport", "departureAirport", "depCode", "dCity"))
        destination = _get(item, ("arrAirportCode", "arrAirport", "arrivalAirport", "arrCode", "aCity"))
        key = (str(flight_no), dep_time.isoformat(), arr_time.isoformat(), price_value)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            FlightLeg(
                origin=origin or watch.outbound_origin,
                destination=destination or watch.outbound_destination,
                date=dep_time.date(),
                flight_no=str(flight_no),
                airline=(_get(item, ("airlineCode", "carrierCode", "carrier", "airline")) or carrier_code),
                departure_time=dep_time,
                arrival_time=arr_time,
                duration_minutes=int((arr_time - dep_time).total_seconds() // 60),
                cabin=watch.cabin,
                price=price_value,
                seats_left=_seats_left(item),
                source="airline_direct",
                booking_url=_get(item, ("bookingUrl", "deepLink", "url", "link")) or "",
            )
        )
    return results


class AirlineDirectSearcher(BaseSearcher, abc.ABC):
    """Base for per-airline Playwright scrapers."""
    source_name = "airline_direct"
    carrier_code: str = ""   # e.g. "CA" — override in subclass

    def _search(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        # TODO: check watch.airlines; skip if carrier_code not in list (or list empty)
        # TODO: call _scrape_with_playwright(watch)
        if watch.airlines and self.carrier_code not in watch.airlines:
            return []
        return self._scrape_with_playwright(watch)

    @abc.abstractmethod
    def _scrape_with_playwright(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        """Subclass launches Playwright and returns results."""


class CAScraper(AirlineDirectSearcher):
    carrier_code = "CA"

    def _scrape_with_playwright(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        # TODO: implement — see module docstring for CA endpoint details
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

        logger.info(
            "airline_direct CA search %s-%s %s",
            watch.outbound_origin,
            watch.outbound_destination,
            watch.outbound_date.isoformat(),
        )
        with sync_playwright() as p:
            launch_kwargs = {"headless": True}
            if self.proxy:
                launch_kwargs["proxy"] = {"server": self.proxy.get("https") or self.proxy.get("http")}
            browser = p.chromium.launch(**launch_kwargs)
            page = browser.new_page()
            results = []
            forbidden = False

            def handle_response(response):
                nonlocal forbidden
                if "searchFlight" in response.url or "flightList" in response.url:
                    if response.status == 403:
                        forbidden = True
                        return
                    try:
                        results.append(response.json())
                    except Exception:
                        pass

            page.on("response", handle_response)
            try:
                page.goto("https://www.airchina.com.cn/cn/booking/search-flight.shtml", wait_until="domcontentloaded")
                page.fill('input[name="dCity"]', watch.outbound_origin)
                page.fill('input[name="aCity"]', watch.outbound_destination)
                page.fill('input[name="depDate"]', watch.outbound_date.strftime("%Y-%m-%d"))
                with page.expect_response(
                    lambda response: "searchFlight" in response.url or "flightList" in response.url,
                    timeout=30000,
                ):
                    page.click('button[type="submit"]')
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                logger.warning("airline_direct CA search timed out waiting for flight response")
                return []
            finally:
                browser.close()

        if forbidden:
            logger.warning("airline_direct CA direct scraper returned 403; skipping")
            return []
        out: list[FlightLeg | RoundTripBundle] = []
        for item in results:
            out.extend(self._parse_response(item, watch))
        return out

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        return _parse_airline_json(raw, watch, self.carrier_code)


class MUScraper(AirlineDirectSearcher):
    carrier_code = "MU"

    def _scrape_with_playwright(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

        trip_type = "RT" if watch.return_date else "OW"
        url = (
            "https://www.ceair.com/booking/flight-search_V4.html#/"
            f"flight-search?tripType={trip_type}&depCity={watch.outbound_origin}"
            f"&arrCity={watch.outbound_destination}&depDate={watch.outbound_date.isoformat()}"
        )
        if watch.return_date:
            url += f"&retDate={watch.return_date.isoformat()}"

        logger.info(
            "airline_direct MU search %s-%s %s",
            watch.outbound_origin,
            watch.outbound_destination,
            watch.outbound_date.isoformat(),
        )
        with sync_playwright() as p:
            launch_kwargs = {"headless": True}
            if self.proxy:
                launch_kwargs["proxy"] = {"server": self.proxy.get("https") or self.proxy.get("http")}
            browser = p.chromium.launch(**launch_kwargs)
            page = browser.new_page()
            results = []
            forbidden = False

            def handle_response(response):
                nonlocal forbidden
                if "/ceas/pc/search" in response.url:
                    if response.status == 403:
                        forbidden = True
                        return
                    try:
                        results.append(response.json())
                    except Exception:
                        pass

            page.on("response", handle_response)
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_response(lambda response: "/ceas/pc/search" in response.url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                logger.warning("airline_direct MU search timed out waiting for flight response")
                return []
            finally:
                browser.close()

        if forbidden:
            logger.warning("airline_direct MU direct scraper returned 403; skipping")
            return []
        out: list[FlightLeg | RoundTripBundle] = []
        for item in results:
            out.extend(self._parse_response(item, watch))
        return out

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        return _parse_airline_json(raw, watch, self.carrier_code)


class CZScraper(AirlineDirectSearcher):
    carrier_code = "CZ"

    def _scrape_with_playwright(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

        logger.info(
            "airline_direct CZ search %s-%s %s",
            watch.outbound_origin,
            watch.outbound_destination,
            watch.outbound_date.isoformat(),
        )
        with sync_playwright() as p:
            launch_kwargs = {"headless": True}
            if self.proxy:
                launch_kwargs["proxy"] = {"server": self.proxy.get("https") or self.proxy.get("http")}
            browser = p.chromium.launch(**launch_kwargs)
            page = browser.new_page()
            results = []
            forbidden = False

            def handle_response(response):
                nonlocal forbidden
                if "searchFlight" in response.url:
                    if response.status == 403:
                        forbidden = True
                        return
                    try:
                        results.append(response.json())
                    except Exception:
                        pass

            page.on("response", handle_response)
            try:
                page.goto("https://www.csair.com/cn/booking/flight_searching.shtml", wait_until="domcontentloaded")
                page.fill("#deptCity", watch.outbound_origin)
                page.fill("#arrvCity", watch.outbound_destination)
                page.fill("#deptDate", watch.outbound_date.strftime("%Y-%m-%d"))
                if watch.return_date:
                    page.fill("#retuDate", watch.return_date.strftime("%Y-%m-%d"))
                with page.expect_response(lambda response: "searchFlight" in response.url, timeout=30000):
                    page.click("#searchBtn")
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                logger.warning("airline_direct CZ search timed out waiting for flight response")
                return []
            finally:
                browser.close()

        if forbidden:
            logger.warning("airline_direct CZ direct scraper returned 403; skipping")
            return []
        out: list[FlightLeg | RoundTripBundle] = []
        for item in results:
            out.extend(self._parse_response(item, watch))
        return out

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        return _parse_airline_json(raw, watch, self.carrier_code)


# Registry: add new airline scrapers here
AIRLINE_SCRAPERS: dict[str, type[AirlineDirectSearcher]] = {
    "CA": CAScraper,
    "MU": MUScraper,
    "CZ": CZScraper,
}
