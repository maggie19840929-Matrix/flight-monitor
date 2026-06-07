"""
APScheduler wrapper — runs Monitor.run_cycle() on a configurable interval.
Codex: implement start().
"""
from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import AppConfig
from .monitor import Monitor

logger = logging.getLogger(__name__)


def start(cfg: AppConfig) -> None:
    """
    Start the blocking scheduler loop.

    Codex:
    1. Instantiate Monitor(cfg).
    2. Create BlockingScheduler with timezone from cfg.scheduler["timezone"].
    3. Add job: monitor.run_cycle, IntervalTrigger(minutes=cfg.scheduler["interval_minutes"]).
    4. Register atexit / SIGTERM handler → monitor.shutdown().
    5. Optionally enforce active_hours: wrap run_cycle to no-op outside window.
    6. Call scheduler.start() (blocks).
    """
    raise NotImplementedError("Codex: implement scheduler.start")
