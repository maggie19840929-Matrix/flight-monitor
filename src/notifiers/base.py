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
    def _price(value: float) -> str:
        return f"{value:.0f}" if float(value).is_integer() else f"{value:.2f}"

    def _duration(minutes: int) -> str:
        hours, mins = divmod(minutes, 60)
        if hours and mins:
            return f"{hours}小时{mins}分钟"
        if hours:
            return f"{hours}小时"
        return f"{mins}分钟"

    def _leg_line(item: FlightLeg, prefix: str = "✈") -> str:
        return "\n".join(
            [
                f"{prefix} {item.flight_no}  {item.origin} → {item.destination}",
                (
                    f"📅 {item.date.isoformat()}  "
                    f"{item.departure_time:%H:%M} → {item.arrival_time:%H:%M}"
                    f"（{_duration(item.duration_minutes)}）"
                ),
                f"💰 ¥{_price(item.price)} 含税（{item.source}）",
            ]
        )

    if isinstance(leg, FlightLeg):
        # TODO: build oneway message
        return "\n".join(
            [
                f"【机票提醒】{alert.watch_id}",
                _leg_line(leg),
                f"🔗 {leg.booking_url}",
            ]
        )
    else:
        # TODO: build roundtrip message showing both legs and total price
        booking_url = leg.bundle_url or leg.outbound.booking_url
        return "\n".join(
            [
                f"【机票提醒】{alert.watch_id}",
                _leg_line(leg.outbound, "✈ 去程"),
                _leg_line(leg.inbound, "✈ 返程"),
                f"💰 合计 ¥{_price(leg.total_price)} 含税（{leg.source}）",
                f"🔗 {booking_url}",
            ]
        )


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
