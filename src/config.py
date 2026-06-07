"""
Config loader — reads config.yaml and returns typed objects.
Codex: implement the TODOs to parse each section.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .models import Cabin, TripType, WatchConfig


def load(path: str | Path = "config.yaml") -> AppConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return AppConfig.from_dict(raw)


class AppConfig:
    def __init__(self, raw: dict[str, Any]):
        self._raw = raw
        # TODO: parse all sections; raise ValueError on missing required fields
        self.watch_list: list[WatchConfig] = self._parse_watch_list()
        self.sources: dict[str, Any] = raw.get("sources", {})
        self.scheduler: dict[str, Any] = raw.get("scheduler", {})
        self.notifiers: dict[str, Any] = raw.get("notifiers", {})
        self.storage: dict[str, Any] = raw.get("storage", {})
        self.proxy: dict[str, Any] = raw.get("proxy", {})
        self.logging: dict[str, Any] = raw.get("logging", {})

    @classmethod
    def from_dict(cls, raw: dict) -> AppConfig:
        return cls(raw)

    def _parse_watch_list(self) -> list[WatchConfig]:
        result = []
        for entry in self._raw.get("watch_list", []):
            # TODO: map YAML dict → WatchConfig dataclass
            # Hint: parse dates with date.fromisoformat()
            try:
                trip_type = TripType(entry["trip_type"])
                outbound = entry["outbound"]

                return_origin = None
                return_destination = None
                return_date = None
                if trip_type == TripType.ROUNDTRIP:
                    inbound = entry["return"]
                    return_origin = inbound["origin"]
                    return_destination = inbound["destination"]
                    return_date = date.fromisoformat(inbound["date"])

                result.append(
                    WatchConfig(
                        id=entry["id"],
                        label=entry["label"],
                        trip_type=trip_type,
                        outbound_origin=outbound["origin"],
                        outbound_destination=outbound["destination"],
                        outbound_date=date.fromisoformat(outbound["date"]),
                        cabin=Cabin(entry["cabin"]),
                        passengers=entry["passengers"],
                        airlines=entry.get("airlines", []),
                        price_threshold=entry["price_threshold"],
                        currency=entry["currency"],
                        return_origin=return_origin,
                        return_destination=return_destination,
                        return_date=return_date,
                    )
                )
            except KeyError as exc:
                raise ValueError(f"Missing required watch_list field: {exc.args[0]}") from exc
        return result

    def proxy_dict(self) -> dict[str, str] | None:
        """Return requests-compatible proxy dict or None."""
        if not self.proxy.get("enabled"):
            return None
        return {
            "http": self.proxy["http"],
            "https": self.proxy["https"],
        }
