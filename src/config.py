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
            raise NotImplementedError("Codex: implement _parse_watch_list")
        return result

    def proxy_dict(self) -> dict[str, str] | None:
        """Return requests-compatible proxy dict or None."""
        if not self.proxy.get("enabled"):
            return None
        return {
            "http": self.proxy["http"],
            "https": self.proxy["https"],
        }
