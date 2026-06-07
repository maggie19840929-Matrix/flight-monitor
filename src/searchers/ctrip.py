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

from typing import Any

import requests

from ..models import FlightLeg, RoundTripBundle, WatchConfig
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
        raise NotImplementedError("Codex: implement CtripSearcher._search")

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        # TODO: walk raw JSON; map each flight item to FlightLeg
        # booking_url pattern: https://www.ctrip.com/online/clk/toBook.aspx?...
        raise NotImplementedError("Codex: implement CtripSearcher._parse_response")
