"""
Telegram Bot 推送 notifier.

API: https://core.telegram.org/bots/api#sendmessage
POST https://api.telegram.org/bot{token}/sendMessage
Body: { chat_id, text, parse_mode, disable_web_page_preview }
"""
from __future__ import annotations

import requests

from ..models import Alert
from .base import BaseNotifier


class TelegramNotifier(BaseNotifier):
    def _send(self, alert: Alert, message: str) -> bool:
        token = self.cfg["token"]
        chat_id = self.cfg["chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        resp = requests.post(url, json=payload, timeout=15)
        return resp.status_code == 200 and resp.json().get("ok")
