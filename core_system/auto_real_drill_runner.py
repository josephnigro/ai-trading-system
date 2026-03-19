"""Auto-run real drill as soon as required credentials are present."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict

from orchestrator import TradingOrchestrator, build_alpaca_broker
from src.notification_module.notification_engine import NotificationModule

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()


def readiness() -> Dict[str, int]:
    load_env_file()
    broker = build_alpaca_broker()
    notify = NotificationModule()
    r = notify.get_transport_readiness()

    return {
        "alpaca_ready": 1 if broker is not None else 0,
        "smtp_ready": 1 if (r["smtp"]["enabled"] and r["smtp"]["ready"]) else 0,
        "polygon_key": 1 if bool(os.getenv("POLYGON_API_KEY") or os.getenv("POLYGONIO_API_KEY")) else 0,
    }


def run_once() -> int:
    broker = build_alpaca_broker()
    orchestrator = TradingOrchestrator(broker=broker)

    ok = orchestrator.initialize(["AAPL", "MSFT", "NVDA", "SOFI", "PLTR"])
    print(f"INIT_OK={1 if ok else 0}")
    if not ok:
        return 1

    result = orchestrator.run_daily_phase2_cycle(
        send_email=True,
        send_sms=False,
        execute_approved=True,
    )
    print("CYCLE_OK=1")
    print(f"PROPOSALS={result.get('proposals_generated', 0)}")
    print(f"EXECUTIONS={result.get('executions', 0)}")
    print(f"RESPONSE_RECEIVED={1 if result.get('response_received') else 0}")

    orchestrator.shutdown()
    print("NO_CRASH=1")
    return 0


def main() -> None:
    print("AUTO_DRILL_WATCHER=STARTED")
    print("Waiting for Alpaca + SMTP readiness...")

    while True:
        r = readiness()
        print(
            f"READINESS alpaca={r['alpaca_ready']} smtp={r['smtp_ready']} polygon={r['polygon_key']}"
        )

        if r["alpaca_ready"] and r["smtp_ready"]:
            print("READINESS_OK=1")
            code = run_once()
            print(f"AUTO_DRILL_EXIT={code}")
            return

        time.sleep(15)


if __name__ == "__main__":
    main()
