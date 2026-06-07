"""
Unit tests for searcher base logic (no network calls).
Codex: add integration tests per searcher using pytest-vcr or recorded fixtures.
"""
from datetime import date

import pytest

from src.models import Cabin, FlightLeg, TripType, WatchConfig
from src.searchers.base import BaseSearcher
from datetime import datetime


def _make_watch(**kwargs) -> WatchConfig:
    defaults = dict(
        id="t1", label="test", trip_type=TripType.ONEWAY,
        outbound_origin="PEK", outbound_destination="SHA",
        outbound_date=date(2026, 7, 15),
        cabin=Cabin.ECONOMY, passengers=1,
        airlines=[], price_threshold=2000, currency="CNY",
    )
    defaults.update(kwargs)
    return WatchConfig(**defaults)


def _make_leg(price: float, airline: str = "CA") -> FlightLeg:
    now = datetime(2026, 7, 15, 8, 0)
    return FlightLeg(
        origin="PEK", destination="SHA", date=date(2026, 7, 15),
        flight_no=f"{airline}1234", airline=airline,
        departure_time=now, arrival_time=now.replace(hour=10),
        duration_minutes=120, cabin=Cabin.ECONOMY,
        price=price, seats_left=5, source="test",
        booking_url="https://example.com",
    )


class _DummySearcher(BaseSearcher):
    source_name = "test"
    def __init__(self):
        super().__init__({}, None)
    def _search(self, watch): return []
    def _parse_response(self, raw, watch): return []


def test_filter_by_price():
    s = _DummySearcher()
    legs = [_make_leg(800), _make_leg(1200), _make_leg(1600)]
    assert len(s._filter_by_price(legs, 1000)) == 1


def test_filter_by_airline_empty_means_all():
    s = _DummySearcher()
    legs = [_make_leg(500, "CA"), _make_leg(500, "MU")]
    assert len(s._filter_by_airline(legs, [])) == 2


def test_filter_by_airline_specific():
    s = _DummySearcher()
    legs = [_make_leg(500, "CA"), _make_leg(500, "MU")]
    assert len(s._filter_by_airline(legs, ["CA"])) == 1
