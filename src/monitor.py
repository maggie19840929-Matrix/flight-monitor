"""
Core monitoring orchestrator — runs one full search cycle.
Codex: implement run_cycle().
"""
from __future__ import annotations

import concurrent.futures
import logging
from datetime import datetime, timedelta

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
        self._last_empty_summary_sent_at: datetime | None = None

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
        summaries: list[tuple[str, WatchConfig, int]] = []
        total_results = 0
        alerts_sent = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._search_one, searcher, watch): (searcher, watch)
                for watch in self.cfg.watch_list
                for searcher in self.searchers
            }
            for future in concurrent.futures.as_completed(futures):
                searcher, watch = futures[future]
                try:
                    results = future.result()
                    result_count = len(results)
                    summaries.append((type(searcher).__name__, watch, result_count))
                    total_results += result_count
                    alerts_sent += self._fire_alerts(watch, results)
                except Exception as exc:
                    summaries.append((type(searcher).__name__, watch, 0))
                    logger.error("Search failed: %s", exc)

        if total_results == 0 and alerts_sent == 0:
            self._send_empty_cycle_summary(summaries)

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
                     results: list[FlightLeg | RoundTripBundle]) -> int:
        sent_count = 0
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
                    sent_count += 1
                    logger.info("Alert sent via %s for %s ¥%.0f", type(notifier).__name__, flight_no, price)
            self.storage.save(watch.id, result)
        return sent_count

    def _send_empty_cycle_summary(self, summaries: list[tuple[str, WatchConfig, int]]) -> None:
        now = datetime.utcnow()
        if self._last_empty_summary_sent_at and now - self._last_empty_summary_sent_at < timedelta(hours=4):
            return

        lines = [
            "【机票监控运行汇总】",
            f"时间：{now.isoformat(timespec='seconds')} UTC",
            "状态：监测正常运行，但本轮没有符合条件的票价结果。",
        ]
        for watch in self.cfg.watch_list:
            route = f"{watch.outbound_origin}→{watch.outbound_destination} {watch.outbound_date.isoformat()}"
            if watch.return_date:
                route += f" / {watch.return_origin}→{watch.return_destination} {watch.return_date.isoformat()}"
            threshold = f"¥{watch.price_threshold:.0f}" if watch.price_threshold is not None else "未设置"
            lines.append(f"监控：{route}，限价 {threshold}")

        lines.append("搜索源结果：")
        for source_name, watch, count in sorted(summaries, key=lambda item: (item[1].id, item[0])):
            lines.append(f"- {source_name}: {count} 条")
        lines.append("说明：只有抓到低于限价的票价时才会发送【机票提醒】。")

        message = "\n".join(lines)
        sent = False
        for notifier in self.notifiers:
            if notifier.send_text(message):
                sent = True
                logger.info("Empty cycle summary sent via %s", type(notifier).__name__)
        if sent:
            self._last_empty_summary_sent_at = now

    def shutdown(self) -> None:
        self.storage.close()
