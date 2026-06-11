"""
飞书自定义机器人 notifier.
API: https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
POST {webhook_url}
Body: {"msg_type": "text", "content": {"text": "..."}}
"""
from __future__ import annotations

import requests

from ..models import Alert
from .base import BaseNotifier


class FeishuNotifier(BaseNotifier):
    def _send(self, alert: Alert, message: str) -> bool:
        return self._send_text(message)

    def _send_text(self, message: str) -> bool:
        resp = requests.post(
            self.cfg["webhook_url"],
            json={"msg_type": "text", "content": {"text": message}},
            timeout=15,
        )
        return resp.status_code == 200 and resp.json().get("code") == 0
