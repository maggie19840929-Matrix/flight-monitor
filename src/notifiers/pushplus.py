"""
PushPlus 微信推送 notifier.
API: https://www.pushplus.plus/doc/

POST https://www.pushplus.plus/send
Body: {"token": "...", "title": "...", "content": "...", "template": "html"}

Codex: implement _send().  Use HTML template for rich formatting (bold, links).
"""
from __future__ import annotations

import requests

from ..models import Alert
from .base import BaseNotifier


class PushPlusNotifier(BaseNotifier):
    _API = "https://www.pushplus.plus/send"

    def _send(self, alert: Alert, message: str) -> bool:
        # TODO: POST JSON; check resp["code"] == 200
        payload = {
            "token": self.cfg["token"],
            "title": "机票提醒",
            "content": message.replace("\n", "<br>"),
            "template": self.cfg.get("template", "html"),
        }
        resp = requests.post(self._API, json=payload, timeout=15)
        return resp.json().get("code") == 200
