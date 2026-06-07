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
        raise NotImplementedError("Codex: implement PushPlusNotifier._send")
