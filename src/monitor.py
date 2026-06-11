"""
Core monitoring orchestrator — runs one full search cycle.
Codex: implement run_cycle().
"""
from __future__ import annotations

import concurrent.futures
import logging
from datetime import datetime

from .config import AppConfig
from .models import Alert, FlightLeg, RoundTripBundle, WatchConfig
from .notifiers import build_notifiers
from .notifiers.base import BaseNotifier
from .searchers import build_searchers
from .searchers.base import BaseSearcher
from .storage import Storage

logger = logging.getLogger(__name__)


class Monitor:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.searchers: list[BaseSearcher] = build_searchers(cfg.sources, cfg.proxy_dict())
        self.notifiers: list[BaseNotifier] = build_notifiers(cfg.notifiers)
        self.storage = Storage(cfg.storage["db_path"])

    def run_cycle(self) -> None:
        """
        One full monitoring cycle:
        1. For each watch in cfg.watch_list, run all searchers in parallel threads.
        2. Merge results; filter by airline + price_threshold.
        3. Deduplicate against storage.already_notified().
        4. Save new results to storage.
        5. Send alerts via all notifiers.

        Codex: implement using concurrent.futures.ThreadPoolExecutor.
        Max workers = len(self.searchers) * len(cfg.watch_list) capped at 8.
        """
        logger.info("Starting monitor cycle at %s", datetime.utcnow().isoformat())
        # TODO: implement full cycle
        max_workers = min(max(len(self.searchers) * len(self.cfg.watch_list), 1), 8)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._search_one, searcher, watch): (searcher, watch)
                for watch in self.cfg.watch_list
                for searcher in self.searchers
            }
            for future in concurrent.futures.as_completed(futures):
                _, watch = futures[future]
                try:
                    results = future.result()
                    self._fire_alerts(watch, results)
                except Exception as exc:
                    logger.error("Search failed: %s", exc)

        self.storage.prune_old(self.cfg.storage.get("keep_history_days", 30))

    def _search_one(self, searcher: BaseSearcher, watch: WatchConfig) -> list:
        """Single searcher × single watch — called in thread pool."""
        results = searcher.search(watch)
        results = searcher._filter_by_airline(results, watch.airlines)
        results = searcher._filter_by_price(results, watch.price_threshold)
        logger.info(
            "Search completed: source=%s watch=%s results=%d",
            type(searcher).__name__,
            watch.id,
            len(results),
        )
        return results

    def _fire_alerts(self, watch: WatchConfig,
                     results: list[FlightLeg | RoundTripBundle]) -> None:
        for result in results:
            flight_no = result.flight_no if isinstance(result, FlightLeg) else result.outbound.flight_no
            price = result.price if isinstance(result, FlightLeg) else result.total_price
            if self.storage.already_notified(watch.id, flight_no, price):
                continue
            alert = Alert(
                watch_id=watch.id,
                triggered_at=datetime.utcnow(),
                leg=result,
                message="",   # filled by notifier
            )
            for notifier in self.notifiers:
                ok = notifier.send(alert)
                if ok:
                    logger.info("Alert sent via %s for %s ¥%.0f", type(notifier).__name__, flight_no, price)
            self.storage.save(watch.id, result)

    def shutdown(self) -> None:
        self.storage.close()
