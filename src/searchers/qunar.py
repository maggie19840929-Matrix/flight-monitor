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

from typing import Any

import requests

from ..models import FlightLeg, RoundTripBundle, WatchConfig
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
        raise NotImplementedError("Codex: implement QunarSearcher._search")

    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        # TODO: iterate raw["data"]["flightList"] → FlightLeg objects
        raise NotImplementedError("Codex: implement QunarSearcher._parse_response")
