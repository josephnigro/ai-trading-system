"""Standalone stress-lab runner (not part of core runtime path)."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT / "core_system"
HISTORY_FILE = ROOT / "stress_lab" / "stress_test_history.jsonl"
REPORT_FILE = ROOT / "stress_lab" / "latest_stress_feedback.md"


def load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()


def run_iteration(index: int, universe: List[str]) -> Dict[str, Any]:
    from orchestrator import TradingOrchestrator, build_alpaca_broker  # type: ignore
    from src.notification_module.notification_engine import NotificationModule  # type: ignore

    result: Dict[str, Any] = {
        "iteration": index,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "init_ok": False,
        "cycle_ok": False,
        "proposals": 0,
        "executions": 0,
        "response_received": False,
        "email_test_sent": False,
        "broker_ready": False,
        "smtp_ready": False,
        "error": "",
        "duration_seconds": 0.0,
    }

    t0 = time.perf_counter()
    try:
        broker = build_alpaca_broker()
        notify = NotificationModule()
        readiness = notify.get_transport_readiness()

        result["broker_ready"] = broker is not None
        result["smtp_ready"] = bool(readiness["smtp"]["enabled"] and readiness["smtp"]["ready"])

        test_send = notify.send_test_digest(send_email=True, send_sms=False)
        result["email_test_sent"] = bool(test_send.get("email_sent"))

        orch = TradingOrchestrator(broker=broker)
        init_ok = orch.initialize(universe)
        result["init_ok"] = bool(init_ok)
        if not init_ok:
            result["error"] = "initialize failed"
            return result

        cycle = orch.run_daily_phase2_cycle(
            send_email=True,
            send_sms=False,
            execute_approved=True,
        )
        result["cycle_ok"] = True
        result["proposals"] = int(cycle.get("proposals_generated", 0) or 0)
        result["executions"] = int(cycle.get("executions", 0) or 0)
        result["response_received"] = bool(cycle.get("response_received", False))

        orch.shutdown()
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        result["duration_seconds"] = round(time.perf_counter() - t0, 2)

    return result


def append_history(rows: List[Dict[str, Any]]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def build_feedback_report(rows: List[Dict[str, Any]]) -> str:
    total = len(rows)
    init_ok = sum(1 for r in rows if r["init_ok"])
    cycle_ok = sum(1 for r in rows if r["cycle_ok"])
    email_ok = sum(1 for r in rows if r["email_test_sent"])
    broker_ok = sum(1 for r in rows if r["broker_ready"])
    smtp_ok = sum(1 for r in rows if r["smtp_ready"])
    proposals = sum(int(r["proposals"]) for r in rows)
    executions = sum(int(r["executions"]) for r in rows)
    avg_seconds = round(sum(float(r["duration_seconds"]) for r in rows) / total, 2) if total else 0.0

    works: List[str] = []
    missing: List[str] = []
    improve: List[str] = []

    if init_ok == total:
        works.append("Initialization stable across all stress iterations.")
    else:
        missing.append("Initialization is intermittently unstable.")

    if email_ok == total:
        works.append("SMTP email transport is sending test messages.")
    else:
        missing.append("Email transport failed in one or more iterations.")

    if broker_ok == total:
        works.append("Alpaca broker credentials and SDK path are available.")
    else:
        missing.append("Alpaca broker was unavailable in one or more iterations.")

    if smtp_ok == total:
        works.append("SMTP readiness stayed configured throughout the test.")
    else:
        missing.append("SMTP readiness dropped in one or more iterations.")

    if proposals > 0:
        works.append("Strategy produced qualified proposals during the stress run.")
    else:
        missing.append("No qualified proposals were generated in this window.")
        improve.append("Track a broader/different ticker universe for test windows to increase proposal hit-rate.")

    if executions > 0:
        works.append("Execution path placed trades through Alpaca during this run.")
    else:
        missing.append("No trades executed (no approved proposals to execute).")
        improve.append("Add a dedicated paper-trade smoke mode that executes one fixed-symbol micro-order for connectivity checks.")

    improve.extend([
        "Store run metadata in JSONL (already enabled) and review weekly trends.",
        "Add per-iteration API-source counters (Polygon success/fallback counts) to quantify data-layer reliability.",
        "Set alert thresholds for repeated 429/403 responses to trigger adaptive scan-size reductions.",
    ])

    lines = [
        "# Stress Test Feedback Loop Report",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Scope",
        "",
        "Standalone stress-lab run only. No integration into core runtime flow.",
        "",
        "## Summary Metrics",
        "",
        f"- Iterations: {total}",
        f"- Init success: {init_ok}/{total}",
        f"- Cycle success: {cycle_ok}/{total}",
        f"- Email test sends: {email_ok}/{total}",
        f"- Broker ready checks: {broker_ok}/{total}",
        f"- SMTP ready checks: {smtp_ok}/{total}",
        f"- Total proposals: {proposals}",
        f"- Total executions: {executions}",
        f"- Avg iteration duration (s): {avg_seconds}",
        "",
        "## What Worked",
        "",
    ]
    lines.extend([f"- {x}" for x in works] or ["- None"]) 

    lines.extend([
        "",
        "## What Is Missing / Failed",
        "",
    ])
    lines.extend([f"- {x}" for x in missing] or ["- None"]) 

    lines.extend([
        "",
        "## Improvement Backlog",
        "",
    ])
    lines.extend([f"- {x}" for x in improve] or ["- None"]) 

    lines.extend([
        "",
        "## Raw Iteration Data (This Run)",
        "",
        "```json",
        json.dumps(rows, indent=2),
        "```",
    ])

    return "\n".join(lines)


def main() -> None:
    load_env_file()

    sys.path.insert(0, str(CORE_DIR))

    default_universe = ["AAPL", "MSFT", "NVDA", "SOFI", "PLTR", "AMD", "TSLA", "AMZN"]
    universe_size = int(os.getenv("STRESS_LAB_UNIVERSE_SIZE", "5"))
    iterations = int(os.getenv("STRESS_LAB_ITERATIONS", "2"))
    universe = default_universe[: max(1, min(len(default_universe), universe_size))]

    rows: List[Dict[str, Any]] = []
    print("STRESS_LAB_START=1")
    try:
        for i in range(1, iterations + 1):
            row = run_iteration(i, universe)
            rows.append(row)
            append_history([row])

            print(f"ITER_{i}_INIT_OK={1 if row['init_ok'] else 0}")
            print(f"ITER_{i}_CYCLE_OK={1 if row['cycle_ok'] else 0}")
            print(f"ITER_{i}_EMAIL_SENT={1 if row['email_test_sent'] else 0}")
            print(f"ITER_{i}_PROPOSALS={row['proposals']}")
            print(f"ITER_{i}_EXECUTIONS={row['executions']}")
            if row["error"]:
                print(f"ITER_{i}_ERROR={row['error']}")
    finally:
        if rows:
            report = build_feedback_report(rows)
            REPORT_FILE.write_text(report, encoding="utf-8")
            print("STRESS_LAB_DONE=1")
            print(f"HISTORY_FILE={HISTORY_FILE}")
            print(f"REPORT_FILE={REPORT_FILE}")


if __name__ == "__main__":
    main()
