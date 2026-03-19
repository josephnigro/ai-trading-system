"""Automated runtime engine for daily scan + periodic position monitoring."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from orchestrator import TradingOrchestrator, build_alpaca_broker

EST = ZoneInfo("America/New_York")
BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "logs" / "system.log"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def setup_logging() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("auto_runner")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def next_scan_time(now_est: datetime) -> datetime:
    target = now_est.replace(hour=16, minute=10, second=0, microsecond=0)
    if now_est >= target:
        target = target + timedelta(days=1)
    return target


def approve_up_to_limit(orchestrator: TradingOrchestrator, approvals_left: int, logger: logging.Logger) -> int:
    if approvals_left <= 0:
        return 0

    pending = orchestrator.get_pending_proposals()
    approved = 0

    for proposal in pending[:approvals_left]:
        ok = orchestrator.approve_trade(proposal.trade_id, notes="AUTO_APPROVE_PAPER")
        if ok:
            approved += 1

    logger.info("Auto-approval complete: approved=%s pending=%s", approved, len(pending))
    return approved


def run_scan_cycle(
    orchestrator: TradingOrchestrator,
    logger: logging.Logger,
    max_trades_per_day: int,
    trades_executed_today: int,
) -> int:
    logger.info("Starting scheduled daily scan cycle")

    proposals = orchestrator.run_scan()
    logger.info("Scan finished: proposals=%s", len(proposals))

    orchestrator.send_daily_proposal_digest(proposals=proposals, send_email=True, send_sms=False)
    logger.info("Daily digest sent (email attempted)")

    auto_approve = env_bool("AUTO_APPROVE_PAPER", default=False)
    kill_switch = env_bool("KILL_SWITCH", default=False)

    if not auto_approve:
        logger.info("AUTO_APPROVE_PAPER disabled, leaving manual approval flow untouched")
        return 0

    approvals_left = max(0, max_trades_per_day - trades_executed_today)
    if approvals_left <= 0:
        logger.warning("Daily trade limit reached (%s), skipping auto-approvals", max_trades_per_day)
        return 0

    approved_count = approve_up_to_limit(orchestrator, approvals_left, logger)
    if approved_count <= 0:
        logger.info("No trades approved by automation")
        return 0

    if kill_switch:
        logger.warning("KILL_SWITCH=1, execution disabled")
        return 0

    executions = orchestrator.execute_approved_trades()
    executed = len(executions)
    logger.info("Execution complete: executed=%s", executed)
    return executed


def run_position_monitor(orchestrator: TradingOrchestrator, logger: logging.Logger) -> None:
    alerts = orchestrator.position_monitor.run_check(
        send_notifications=True,
        notification_module=orchestrator.notification_module,
    )
    logger.info("Position monitor run complete: alerts=%s", len(alerts))


def main() -> None:
    logger = setup_logging()
    logger.info("Auto runner starting")

    max_trades_per_day = int(os.getenv("MAX_TRADES_PER_DAY", "3"))

    orchestrator: TradingOrchestrator | None = None
    initialized = False

    last_scan_day = None
    last_monitor_ts = 0.0
    trades_executed_today = 0
    last_trade_day = None

    try:
        while True:
            try:
                now_est = datetime.now(EST)

                if last_trade_day != now_est.date():
                    trades_executed_today = 0
                    last_trade_day = now_est.date()

                if orchestrator is None:
                    broker = build_alpaca_broker()
                    orchestrator = TradingOrchestrator(broker=broker)
                    initialized = False

                if not initialized:
                    initialized = orchestrator.initialize()
                    if initialized:
                        logger.info("Orchestrator initialized")
                    else:
                        logger.error("Initialization failed, retrying in 60s")
                        time.sleep(60)
                        continue

                # Run position monitor every 10 minutes.
                if time.time() - last_monitor_ts >= 600:
                    try:
                        run_position_monitor(orchestrator, logger)
                    except Exception as exc:
                        logger.exception("Position monitor error: %s", exc)
                    finally:
                        last_monitor_ts = time.time()

                # Run one scan per day after 4:10 PM EST.
                should_run_scan = (
                    last_scan_day != now_est.date()
                    and (now_est.hour > 16 or (now_est.hour == 16 and now_est.minute >= 10))
                )
                if should_run_scan:
                    try:
                        executed = run_scan_cycle(
                            orchestrator=orchestrator,
                            logger=logger,
                            max_trades_per_day=max_trades_per_day,
                            trades_executed_today=trades_executed_today,
                        )
                        trades_executed_today += executed
                        last_scan_day = now_est.date()
                        logger.info(
                            "Daily cycle complete: executed_today=%s max_per_day=%s",
                            trades_executed_today,
                            max_trades_per_day,
                        )
                    except Exception as exc:
                        logger.exception("Daily cycle error: %s", exc)

                # Heartbeat every minute with next scan ETA.
                target = next_scan_time(now_est)
                eta_minutes = int((target - now_est).total_seconds() // 60)
                logger.info("Heartbeat: next_scan_in_minutes=%s", eta_minutes)

                time.sleep(60)

            except Exception as loop_exc:
                logger.exception("Main loop error (continuing): %s", loop_exc)
                time.sleep(30)
    finally:
        if orchestrator is not None and initialized:
            try:
                orchestrator.shutdown()
                logger.info("Orchestrator shutdown complete")
            except Exception as shutdown_exc:
                logger.exception("Shutdown error: %s", shutdown_exc)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Stop by user request.
        pass
