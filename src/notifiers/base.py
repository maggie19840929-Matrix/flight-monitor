"""Abstract notifier."""
from __future__ import annotations

import abc
from typing import Any

from ..models import Alert, FlightLeg, RoundTripBundle


def format_message(alert: Alert) -> str:
    """
    Render a human-readable push message from an Alert.
    Codex: implement a clear Chinese-language template, e.g.:

    【机票提醒】{label}
    ✈ {flight_no}  {origin}→{dest}
    📅 {date}  {dep_time}→{arr_time}
    💰 ¥{price} （{source}）
    🔗 {booking_url}
    """
    leg = alert.leg
    if isinstance(leg, FlightLeg):
        # TODO: build oneway message
        raise NotImplementedError("Codex: implement format_message for FlightLeg")
    else:
        # TODO: build roundtrip message showing both legs and total price
        raise NotImplementedError("Codex: implement format_message for RoundTripBundle")


class BaseNotifier(abc.ABC):
    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg

    def send(self, alert: Alert) -> bool:
        """Send notification. Returns True on success."""
        msg = format_message(alert)
        try:
            return self._send(alert, msg)
        except Exception as exc:
            # TODO: log exc
            return False

    @abc.abstractmethod
    def _send(self, alert: Alert, message: str) -> bool:
        """Source-specific send implementation."""
