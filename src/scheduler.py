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
    import atexit
    import signal
    from zoneinfo import ZoneInfo

    monitor = Monitor(cfg)
    tz = ZoneInfo(cfg.scheduler["timezone"])

    def _within_active_hours() -> bool:
        active_hours = cfg.scheduler.get("active_hours", {})
        start_hour = active_hours.get("start", 0)
        end_hour = active_hours.get("end", 24)
        h = datetime.now(tz).hour
        return start_hour <= h < end_hour

    def _job() -> None:
        if _within_active_hours():
            monitor.run_cycle()
        else:
            logger.info("Skipping monitor cycle outside active hours")

    sched = BlockingScheduler(timezone=tz)
    sched.add_job(_job, IntervalTrigger(minutes=cfg.scheduler["interval_minutes"]))
    atexit.register(monitor.shutdown)

    def _shutdown(*_: object) -> None:
        monitor.shutdown()
        sched.shutdown()

    signal.signal(signal.SIGTERM, _shutdown)
    sched.start()
