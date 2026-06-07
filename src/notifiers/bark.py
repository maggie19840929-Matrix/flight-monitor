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
        lines = message.splitlines()
        title = lines[0] if lines else "机票提醒"
        body = "\n".join(lines[1:])
        leg = alert.leg
        booking_url = leg.booking_url if isinstance(leg, FlightLeg) else (leg.bundle_url or leg.outbound.booking_url)
        url = (
            f"{cfg['server'].rstrip('/')}/{cfg['device_key']}/"
            f"{urllib.parse.quote(title, safe='')}/{urllib.parse.quote(body, safe='')}"
        )
        params = {
            "sound": cfg.get("sound", ""),
            "icon": cfg.get("icon", ""),
            "url": urllib.parse.quote(booking_url, safe=""),
        }
        resp = requests.get(url, params=params, timeout=10)
        return resp.status_code == 200
