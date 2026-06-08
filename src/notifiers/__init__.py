"""Notifier factory."""
from __future__ import annotations

from typing import Any

from .base import BaseNotifier
from .bark import BarkNotifier
from .email_notifier import EmailNotifier
from .feishu import FeishuNotifier
from .pushplus import PushPlusNotifier
from .telegram import TelegramNotifier


def build_notifiers(notifiers_cfg: dict[str, Any]) -> list[BaseNotifier]:
    """
    Codex: instantiate each enabled notifier.
    Pattern: if notifiers_cfg["bark"]["enabled"] → append BarkNotifier(cfg["bark"])
    """
    # TODO: implement
    out: list[BaseNotifier] = []
    if notifiers_cfg.get("bark", {}).get("enabled"):
        out.append(BarkNotifier(notifiers_cfg["bark"]))
    if notifiers_cfg.get("pushplus", {}).get("enabled"):
        out.append(PushPlusNotifier(notifiers_cfg["pushplus"]))
    if notifiers_cfg.get("telegram", {}).get("enabled"):
        out.append(TelegramNotifier(notifiers_cfg["telegram"]))
    if notifiers_cfg.get("feishu", {}).get("enabled"):
        out.append(FeishuNotifier(notifiers_cfg["feishu"]))
    if notifiers_cfg.get("email", {}).get("enabled"):
        out.append(EmailNotifier(notifiers_cfg["email"]))
    return out
