import sys
import os
import time
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Make core_system importable from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent / "core_system"))

from orchestrator import TradingOrchestrator, build_alpaca_broker

SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
log = logging.getLogger("main")


def main():
    log.info("=== AI Trading Bot starting ===")

    broker = build_alpaca_broker()
    orchestrator = TradingOrchestrator(broker=broker)
    orchestrator.initialize()
    log.info("Orchestrator initialized. Scan interval: %ss", SCAN_INTERVAL)

    while True:
        try:
            log.info("Running scan...")
            proposals = orchestrator.run_scan()
            log.info("Scan complete — proposals: %s", len(proposals))
        except Exception as exc:
            log.error("Scan error: %s", exc, exc_info=True)

        log.info("Sleeping %ss until next scan", SCAN_INTERVAL)
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
