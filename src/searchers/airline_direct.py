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
from typing import Any

from ..models import FlightLeg, RoundTripBundle, WatchConfig
from .base import BaseSearcher


class AirlineDirectSearcher(BaseSearcher, abc.ABC):
    """Base for per-airline Playwright scrapers."""
    source_name = "airline_direct"
    carrier_code: str = ""   # e.g. "CA" — override in subclass

    def _search(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        # TODO: check watch.airlines; skip if carrier_code not in list (or list empty)
        # TODO: call _scrape_with_playwright(watch)
        raise NotImplementedError

    @abc.abstractmethod
    def _scrape_with_playwright(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        """Subclass launches Playwright and returns results."""


class CAScraper(AirlineDirectSearcher):
    carrier_code = "CA"

    def _scrape_with_playwright(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        # TODO: implement — see module docstring for CA endpoint details
        raise NotImplementedError("Codex: implement CAScraper")

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        raise NotImplementedError("Codex: implement CAScraper._parse_response")


class MUScraper(AirlineDirectSearcher):
    carrier_code = "MU"

    def _scrape_with_playwright(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        raise NotImplementedError("Codex: implement MUScraper")

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        raise NotImplementedError("Codex: implement MUScraper._parse_response")


class CZScraper(AirlineDirectSearcher):
    carrier_code = "CZ"

    def _scrape_with_playwright(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        raise NotImplementedError("Codex: implement CZScraper")

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        raise NotImplementedError("Codex: implement CZScraper._parse_response")


# Registry: add new airline scrapers here
AIRLINE_SCRAPERS: dict[str, type[AirlineDirectSearcher]] = {
    "CA": CAScraper,
    "MU": MUScraper,
    "CZ": CZScraper,
}
