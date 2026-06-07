"""
SQLite price history storage.
Codex: implement all methods using the sqlite3 standard library.

Schema (create on first run):
  CREATE TABLE IF NOT EXISTS price_history (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      watch_id    TEXT NOT NULL,
      flight_no   TEXT NOT NULL,
      source      TEXT NOT NULL,
      cabin       TEXT NOT NULL,
      price       REAL NOT NULL,
      seats_left  INTEGER,
      booking_url TEXT,
      scraped_at  TEXT NOT NULL   -- ISO-8601 UTC
  );

  CREATE INDEX IF NOT EXISTS idx_watch_flight
      ON price_history (watch_id, flight_no, scraped_at);
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .models import FlightLeg, RoundTripBundle, WatchConfig


class Storage:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        # TODO: execute CREATE TABLE and CREATE INDEX statements above
        raise NotImplementedError("Codex: implement _init_schema")

    def save(self, watch_id: str, result: FlightLeg | RoundTripBundle) -> None:
        """Persist a search result to the DB."""
        # TODO: INSERT INTO price_history; use executemany for RoundTripBundle (2 rows)
        raise NotImplementedError("Codex: implement Storage.save")

    def already_notified(self, watch_id: str, flight_no: str, price: float,
                         within_hours: int = 4) -> bool:
        """
        Return True if we already sent an alert for this flight at this price
        within the last `within_hours` hours (prevents duplicate pushes).
        Codex: query price_history; compare scraped_at timestamp.
        """
        raise NotImplementedError("Codex: implement Storage.already_notified")

    def prune_old(self, keep_days: int = 30) -> None:
        """Delete rows older than keep_days days."""
        raise NotImplementedError("Codex: implement Storage.prune_old")

    def close(self) -> None:
        self.conn.close()
