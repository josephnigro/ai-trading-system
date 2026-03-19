"""
Daily Scheduler — AI Trading Scanner

Runs the full daily cycle at a scheduled time each weekday:
  1. Scan the market for trade setups
  2. Send HTML email digest with trade details and approval instructions
  3. Poll inbox for user approval response (up to --response-window minutes)
  4. Execute approved trades
  5. Send execution confirmation email

Usage:
    # Run every day at 09:00 AM (default)
    python daily_scheduler.py --send-email --execute-approved

    # Custom time
    python daily_scheduler.py --run-at 08:30 --send-email --execute-approved

    # Run immediately right now (no schedule, useful for testing)
    python daily_scheduler.py --now --send-email --execute-approved

    # Dry run — scan and email but do NOT execute
    python daily_scheduler.py --now --send-email

Scheduler keeps running indefinitely; kill with Ctrl+C.
"""

import argparse
import logging
import time
import sys
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

import schedule
from dotenv import load_dotenv

from orchestrator import TradingOrchestrator, OrchestratorConfig, build_alpaca_broker
from src.position_monitor.position_monitor import PositionMonitor
from src.position_monitor.position_store import PositionStore
from src.performance_tracker import PerformanceTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("DailyScheduler")

# ── Globals set from CLI args ──────────────────────────────────────────────────
_args: Optional[argparse.Namespace] = None


# ──────────────────────────────────────────────────────────────────────────────
# Core daily job
# ──────────────────────────────────────────────────────────────────────────────

def run_monitor_job() -> None:
    """
    Hourly position monitor job.
    Checks all open positions against their stop/target levels and sends alerts.
    """
    now = datetime.now()
    # Only run during extended market hours (7 AM – 9 PM ET on weekdays)
    if not _args.weekends and now.weekday() >= 5:
        return
    if not (7 <= now.hour < 21):
        return

    logger.info(f"Position monitor check — {now.strftime('%I:%M %p')}")
    try:
        from src.notification_module.notification_engine import NotificationModule
        broker = build_alpaca_broker() if _args.alpaca else None
        store = PositionStore()
        tracker = PerformanceTracker(starting_equity=float(_args.account_size))
        monitor = PositionMonitor(
            broker=broker,
            store=store,
            performance_tracker=tracker,
            auto_close_stops=_args.auto_close_stops,
            auto_close_targets=_args.auto_close_targets,
        )
        nm = NotificationModule()
        alerts = monitor.run_check(
            send_notifications=_args.send_email or _args.send_sms,
            notification_module=nm,
        )
        if alerts:
            for a in alerts:
                d = a.to_dict()
                logger.warning(
                    f"ALERT [{d['alert_type'].upper()}] {d['ticker']} "
                    f"@ ${d['current_price']:.2f} — P&L: ${d['unrealized_pl']:+.2f}"
                )
        else:
            logger.info("Position monitor: all positions within range")
    except Exception as exc:
        logger.error(f"Position monitor job error: {exc}", exc_info=True)


def run_daily_job() -> None:
    """Execute the full daily trading cycle."""
    now = datetime.now()

    # Skip weekends if not forced with --weekends
    if not _args.weekends and now.weekday() >= 5:
        logger.info("Weekend — skipping daily run (use --weekends to override)")
        return

    logger.info("=" * 70)
    logger.info(f"Daily job starting — {now.strftime('%A, %B %d, %Y at %I:%M %p')}")
    logger.info("=" * 70)

    # ── 1. Build orchestrator ──────────────────────────────────────────────────
    config = OrchestratorConfig(
        account_size=float(_args.account_size),
        risk_per_trade_pct=float(_args.risk_pct),
        max_concurrent_positions=int(_args.max_positions),
        data_period="1y",
    )

    broker = None
    if _args.alpaca:
        broker = build_alpaca_broker()
        if broker is None:
            logger.warning("--alpaca requested but credentials not found in .env; execution will be skipped")
        else:
            logger.info("Alpaca paper broker initialised")

    orchestrator = TradingOrchestrator(config=config, broker=broker)

    if not orchestrator.initialize():
        logger.error("Orchestrator initialization failed — aborting daily run")
        return

    if _args.scan_limit > 0:
        orchestrator.stock_universe = orchestrator.stock_universe[: _args.scan_limit]

    try:
        # ── 2. Scan + send digest ─────────────────────────────────────────────
        logger.info("Running market scan...")
        proposals = orchestrator.run_scan()
        n = len(proposals)
        logger.info(f"Scan complete — {n} proposal(s) generated")

        perf_tracker = PerformanceTracker(starting_equity=float(_args.account_size))
        perf_html = perf_tracker.build_stats_html()

        orchestrator.notification_module.publish_trade_digest(
            proposals,
            send_email=_args.send_email,
            send_sms=_args.send_sms,
            performance_html=perf_html,
        )

        if n == 0:
            logger.info("No trade setups today — digest sent, nothing to execute")
            return

        # ── 3. Poll for response ──────────────────────────────────────────────
        inbox_dir = _args.response_inbox or str(
            orchestrator.notification_module.inbox_dir
        )
        response: Optional[str] = None

        if not _args.no_wait:
            logger.info(
                f"Polling inbox every {_args.poll_interval}s "
                f"for up to {_args.response_window} minutes: {inbox_dir}"
            )
            response = _poll_for_response(
                orchestrator,
                inbox_dir=inbox_dir,
                window_minutes=_args.response_window,
                poll_interval_seconds=_args.poll_interval,
            )
        else:
            logger.info("--no-wait set: skipping response poll")

        # ── 4. Process approval ───────────────────────────────────────────────
        executions: List[dict] = []
        if response:
            logger.info(f"Response received: '{response}'")
            approval = orchestrator.process_user_approval_response(response)
            logger.info(f"Approval result: {approval}")

            if _args.execute_approved:
                records = orchestrator.execute_approved_trades()
                executions = [r.to_dict() for r in records if hasattr(r, "to_dict")]
                logger.info(f"{len(executions)} trade(s) executed")
        else:
            logger.info("No response received — trades NOT executed")

        # ── 5. Send confirmation ──────────────────────────────────────────────
        if executions:
            outcome = orchestrator.notification_module.send_execution_confirmation(
                executions,
                send_email=_args.send_email,
                send_sms=_args.send_sms,
            )
            logger.info(f"Confirmation sent: {outcome}")

        logger.info("Daily job complete")

    except Exception as exc:
        logger.error(f"Daily job error: {exc}", exc_info=True)
    finally:
        orchestrator.shutdown()


def _poll_for_response(
    orchestrator: TradingOrchestrator,
    inbox_dir: str,
    window_minutes: int,
    poll_interval_seconds: int,
) -> Optional[str]:
    """
    Poll the inbox directory for a user response file.
    Returns the response string once found, or None if window expires.
    """
    deadline = datetime.now() + timedelta(minutes=window_minutes)
    logger.info(f"Waiting until {deadline.strftime('%I:%M %p')} for approval response...")

    while datetime.now() < deadline:
        response = orchestrator.notification_module.ingest_latest_response(inbox_dir, archive=True)
        if response:
            return response
        remaining = int((deadline - datetime.now()).total_seconds() / 60)
        logger.info(f"No response yet — {remaining} min remaining. Checking again in {poll_interval_seconds}s...")
        time.sleep(poll_interval_seconds)

    logger.info("Response window expired with no response")
    return None


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Trading Scanner — Daily Scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # When to run
    parser.add_argument(
        "--run-at",
        type=str,
        default="09:00",
        metavar="HH:MM",
        help="Time to run daily scan in 24-hour format (default: 09:00)",
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run the job immediately once instead of waiting for schedule",
    )
    parser.add_argument(
        "--weekends",
        action="store_true",
        help="Also run on Saturdays and Sundays",
    )

    # What to do
    parser.add_argument("--send-email", action="store_true", help="Send digest email")
    parser.add_argument("--send-sms", action="store_true", help="Send digest SMS")
    parser.add_argument(
        "--execute-approved",
        action="store_true",
        help="Execute approved trades after approval (requires broker configured)",
    )
    parser.add_argument(
        "--alpaca",
        action="store_true",
        help="Wire in AlpacaBroker for real paper/live order execution",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Send digest and exit without waiting for approval response",
    )

    # Response collection
    parser.add_argument(
        "--response-inbox",
        type=str,
        default=None,
        help="Custom inbox directory for response files (default: logs/notifications/inbox)",
    )
    parser.add_argument(
        "--response-window",
        type=int,
        default=120,
        metavar="MINUTES",
        help="How many minutes to wait for a response (default: 120)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        metavar="SECONDS",
        help="How often to check inbox for new responses (default: 60)",
    )

    # Scan tuning
    parser.add_argument(
        "--scan-limit",
        type=int,
        default=0,
        help="Limit number of symbols scanned (0 = all, default: 0)",
    )
    parser.add_argument("--account-size", type=float, default=200000.0, help="Account size in dollars")
    parser.add_argument("--risk-pct", type=float, default=1.0, help="Risk per trade as pct of account")
    parser.add_argument("--max-positions", type=int, default=3, help="Max concurrent positions")

    # Position monitor
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Run the position monitor hourly (checks stops/targets on open positions)",
    )
    parser.add_argument(
        "--monitor-now",
        action="store_true",
        help="Run the position monitor once immediately and exit",
    )
    parser.add_argument(
        "--auto-close-stops",
        action="store_true",
        help="Automatically close positions that hit their stop loss",
    )
    parser.add_argument(
        "--auto-close-targets",
        action="store_true",
        help="Automatically close positions that hit their profit target",
    )

    return parser


def main() -> None:
    global _args
    load_dotenv()
    _args = _build_parser().parse_args()

    # Validate --run-at format
    try:
        hour, minute = [int(x) for x in _args.run_at.split(":")]
        assert 0 <= hour <= 23 and 0 <= minute <= 59
    except Exception:
        logger.error(f"Invalid --run-at time '{_args.run_at}'. Use HH:MM format, e.g. 09:00")
        sys.exit(1)

    if _args.now:
        # Run immediately and exit
        logger.info("--now flag set: running job immediately")
        run_daily_job()
        return

    if _args.monitor_now:
        logger.info("--monitor-now flag set: running position monitor immediately")
        run_monitor_job()
        return

    # ── Schedule and loop ─────────────────────────────────────────────────────
    run_time = f"{hour:02d}:{minute:02d}"
    schedule.every().day.at(run_time).do(run_daily_job)

    if _args.monitor:
        schedule.every(1).hours.do(run_monitor_job)
        logger.info("Position monitor scheduled: every 1 hour (7 AM – 9 PM on weekdays)")

    next_run = schedule.next_run()
    logger.info(
        f"Daily scheduler started. Job scheduled at {run_time} every day. "
        f"Next run: {next_run.strftime('%A, %B %d at %I:%M %p') if next_run else 'unknown'}."
    )
    logger.info("Press Ctrl+C to stop.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    main()
