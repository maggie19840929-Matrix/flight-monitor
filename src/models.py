"""
Data models — all core domain types live here.
Codex: implement field validation in __post_init__ where marked TODO.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class TripType(str, Enum):
    ONEWAY = "oneway"
    ROUNDTRIP = "roundtrip"


class Cabin(str, Enum):
    ECONOMY = "economy"
    BUSINESS = "business"
    FIRST = "first"


@dataclass
class FlightLeg:
    """Single flight leg (one direction)."""
    origin: str          # IATA airport code, e.g. "PEK"
    destination: str
    date: date
    flight_no: str       # e.g. "CA1234"
    airline: str         # IATA carrier code, e.g. "CA"
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    cabin: Cabin
    price: float         # per-passenger, tax-inclusive, CNY
    seats_left: int      # -1 if unknown
    source: str          # e.g. "ctrip", "qunar", "airline_direct"
    booking_url: str     # deep-link to booking page
    scraped_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        # TODO: validate IATA codes are 2-3 uppercase letters
        # TODO: assert arrival_time > departure_time
        # TODO: assert price >= 0
        assert self.arrival_time > self.departure_time
        assert self.price >= 0
        self.airline = self.airline.upper()


@dataclass
class RoundTripBundle:
    """Paired outbound + return legs as one bookable unit."""
    outbound: FlightLeg
    inbound: FlightLeg
    total_price: float   # outbound.price + inbound.price
    bundle_url: Optional[str] = None  # combined booking URL if available

    @property
    def source(self) -> str:
        return self.outbound.source


@dataclass
class WatchConfig:
    """Parsed representation of one entry in config.yaml watch_list."""
    id: str
    label: str
    trip_type: TripType
    outbound_origin: str
    outbound_destination: str
    outbound_date: date
    cabin: Cabin
    passengers: int
    airlines: list[str]       # empty = all airlines
    price_threshold: float
    currency: str
    return_origin: Optional[str] = None
    return_destination: Optional[str] = None
    return_date: Optional[date] = None

    def __post_init__(self):
        if self.trip_type == TripType.ROUNDTRIP:
            # TODO: assert return fields are set and return_date > outbound_date
            assert self.return_origin is not None
            assert self.return_destination is not None
            assert self.return_date is not None
            assert self.return_date > self.outbound_date


@dataclass
class Alert:
    """Represents a triggered notification."""
    watch_id: str
    triggered_at: datetime
    leg: FlightLeg | RoundTripBundle
    message: str
    sent: bool = False
