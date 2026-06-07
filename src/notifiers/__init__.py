"""Notifier factory."""
from __future__ import annotations

from typing import Any

from .base import BaseNotifier
from .bark import BarkNotifier
from .pushplus import PushPlusNotifier


def build_notifiers(notifiers_cfg: dict[str, Any]) -> list[BaseNotifier]:
    """
    Codex: instantiate each enabled notifier.
    Pattern: if notifiers_cfg["bark"]["enabled"] → append BarkNotifier(cfg["bark"])
    """
    # TODO: implement
    raise NotImplementedError("Codex: implement build_notifiers")
    return []
