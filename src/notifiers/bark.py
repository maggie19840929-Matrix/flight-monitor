"""
Bark iOS push notifier.
API doc: https://bark.day.app/#/tutorial

Push URL: {server}/{device_key}/{title}/{body}?sound={sound}&icon={icon}&url={booking_url}

Codex: implement _send() — encode the booking URL as a query param so tapping
the notification opens the booking page directly in Safari.
"""
from __future__ import annotations

import urllib.parse

import requests

from ..models import Alert, FlightLeg
from .base import BaseNotifier


class BarkNotifier(BaseNotifier):
    def _send(self, alert: Alert, message: str) -> bool:
        cfg = self.cfg
        # TODO: build push URL; POST or GET to Bark server; return True on 200
        raise NotImplementedError("Codex: implement BarkNotifier._send")
