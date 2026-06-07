"""
Abstract base class for all flight searchers.
Each searcher implements search() for one data source.
"""
from __future__ import annotations

import abc
import random
import time
from typing import Any

from ..models import FlightLeg, RoundTripBundle, WatchConfig


class BaseSearcher(abc.ABC):
    source_name: str = ""   # e.g. "ctrip" — override in subclass

    def __init__(self, source_cfg: dict[str, Any], proxy: dict | None):
        self.cfg = source_cfg
        self.proxy = proxy

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        """Entry point called by the monitor. Handles jitter + error catch."""
        self._jitter()
        try:
            return self._search(watch)
        except Exception as exc:
            # TODO: log exc with source_name and watch.id; return []
            return []

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def _search(self, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        """Perform the actual search and return raw results."""

    @abc.abstractmethod
    def _parse_response(self, raw: Any, watch: WatchConfig) -> list[FlightLeg | RoundTripBundle]:
        """Parse source-specific response into domain models."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _jitter(self, base_seconds: float = 2.0) -> None:
        time.sleep(base_seconds + random.uniform(0, 1.5))

    def _filter_by_airline(
        self, results: list[FlightLeg | RoundTripBundle], airlines: list[str]
    ) -> list[FlightLeg | RoundTripBundle]:
        if not airlines:
            return results
        return [
            r for r in results
            if (r.airline if isinstance(r, FlightLeg) else r.outbound.airline) in airlines
        ]

    def _filter_by_price(
        self, results: list[FlightLeg | RoundTripBundle], threshold: float
    ) -> list[FlightLeg | RoundTripBundle]:
        return [
            r for r in results
            if (r.price if isinstance(r, FlightLeg) else r.total_price) <= threshold
        ]
