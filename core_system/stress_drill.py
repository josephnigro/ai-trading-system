"""End-to-end stress drill for current trading system readiness."""

from __future__ import annotations

import os
import time
from statistics import mean

from orchestrator import TradingOrchestrator, build_alpaca_broker


def run_stress_drill(scan_rounds: int = 3) -> None:
    broker = build_alpaca_broker()
    orchestrator = TradingOrchestrator(broker=broker)

    init_ok = orchestrator.initialize()
    print(f"INIT_OK={init_ok}")
    if not init_ok:
        return

    durations = []
    proposal_counts = []

    for idx in range(scan_rounds):
        t0 = time.perf_counter()
        proposals = orchestrator.run_scan()
        dt = time.perf_counter() - t0

        durations.append(dt)
        proposal_counts.append(len(proposals))

        print(f"SCAN_{idx + 1}_COMPLETED=1")
        print(f"SCAN_{idx + 1}_SECONDS={dt:.2f}")
        print(f"SCAN_{idx + 1}_PROPOSALS={len(proposals)}")

    pending = orchestrator.get_pending_proposals()
    print(f"PENDING_PROPOSALS={len(pending)}")

    approved = 0
    for proposal in pending:
        if orchestrator.approve_trade(proposal.trade_id, "stress drill auto-approve"):
            approved += 1
    print(f"APPROVED_COUNT={approved}")

    executions = orchestrator.execute_approved_trades()
    print(f"EXECUTIONS={len(executions)}")
    print(f"BROKER_CONFIGURED={1 if broker is not None else 0}")

    # Try to send digest through configured transports (may be skipped by config).
    message = orchestrator.send_daily_proposal_digest(
        proposals=pending,
        send_email=True,
        send_sms=False,
    )
    print(f"DIGEST_BUILT={1 if bool(message) else 0}")

    if durations:
        print(f"SCAN_AVG_SECONDS={mean(durations):.2f}")
        print(f"SCAN_MAX_SECONDS={max(durations):.2f}")
        print(f"SCAN_MIN_SECONDS={min(durations):.2f}")

    print(f"POLYGON_KEY_PRESENT={1 if bool(os.getenv('POLYGON_API_KEY') or os.getenv('POLYGONIO_API_KEY')) else 0}")

    orchestrator.shutdown()
    print("NO_CRASH=1")


if __name__ == "__main__":
    run_stress_drill(scan_rounds=3)
