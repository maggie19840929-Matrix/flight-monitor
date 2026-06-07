#!/usr/bin/env python3
"""
Entry point.

Usage:
  python main.py                     # start continuous monitoring
  python main.py --once              # run one cycle and exit (useful for cron)
  python main.py --config my.yaml    # use alternate config file
"""
import argparse
import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(cfg_logging: dict) -> None:
    level = getattr(logging, cfg_logging.get("level", "INFO"))
    log_file = cfg_logging.get("file", "logs/monitor.log")
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=cfg_logging.get("max_bytes", 10_485_760),
        backupCount=cfg_logging.get("backup_count", 5),
    )
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Flight price monitor")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    args = parser.parse_args()

    from src.config import load
    cfg = load(args.config)
    setup_logging(cfg.logging)

    if args.once:
        from src.monitor import Monitor
        m = Monitor(cfg)
        try:
            m.run_cycle()
        finally:
            m.shutdown()
    else:
        from src import scheduler
        scheduler.start(cfg)


if __name__ == "__main__":
    main()
