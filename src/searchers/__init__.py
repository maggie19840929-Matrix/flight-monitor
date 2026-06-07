"""
Searcher factory — returns enabled searcher instances from config.
Codex: implement build_searchers().
"""
from __future__ import annotations

from typing import Any

from .base import BaseSearcher
from .ctrip import CtripSearcher
from .fliggy import FliggySearcher
from .qunar import QunarSearcher
from .airline_direct import AIRLINE_SCRAPERS, AirlineDirectSearcher


def build_searchers(sources_cfg: dict[str, Any], proxy: dict | None) -> list[BaseSearcher]:
    """
    Instantiate and return all enabled searchers.
    Codex: iterate sources_cfg; for airline_direct, instantiate one scraper
    per carrier in AIRLINE_SCRAPERS.
    """
    searchers: list[BaseSearcher] = []
    # TODO: if sources_cfg["ctrip"]["enabled"] → append CtripSearcher(...)
    # TODO: if sources_cfg["qunar"]["enabled"] → append QunarSearcher(...)
    # TODO: if sources_cfg["airline_direct"]["enabled"]:
    #           for carrier_code, ScrClass in AIRLINE_SCRAPERS.items():
    #               append ScrClass(sources_cfg["airline_direct"], proxy)
    if sources_cfg.get("ctrip", {}).get("enabled"):
        searchers.append(CtripSearcher(sources_cfg["ctrip"], proxy))
    if sources_cfg.get("qunar", {}).get("enabled"):
        searchers.append(QunarSearcher(sources_cfg["qunar"], proxy))
    if sources_cfg.get("fliggy", {}).get("enabled"):
        searchers.append(FliggySearcher(sources_cfg["fliggy"], proxy))
    if sources_cfg.get("airline_direct", {}).get("enabled"):
        for carrier_code, ScrClass in AIRLINE_SCRAPERS.items():
            searchers.append(ScrClass(sources_cfg["airline_direct"], proxy))
    return searchers
