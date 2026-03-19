"""Daily scheduler for scan, digest delivery, response polling, and execution.

Usage:
  python daily_runner.py                        # Start on schedule (default 4:30 PM)
  python daily_runner.py --run-now              # Run a scan immediately, then keep looping
  python daily_runner.py --schedule 16:30       # Custom scan time  HH:MM  (24-hour, local clock)
  python daily_runner.py --poll-interval 10     # Check inbox every 10 minutes (default: 15)
  python daily_runner.py --execute-approved     # Auto-execute approved trades (requires broker)
  python daily_runner.py --scan-limit 30        # Cap symbols scanned per run (default: 40)
  python daily_runner.py --no-email             # Skip email (useful for dry-run testing)
  python daily_runner.py --send-sms             # Enable Twilio SMS alongside email
  python daily_runner.py --account-size 50000   # Override account size from CLI
"""

import argparse
import logging
import signal
import sys
import time
from datetime import date, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

from orchestrator import TradingOrchestrator, OrchestratorConfig


# OUTPUT

def _setup_logging(log_dir: str = "logs") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            f"{log_dir}/daily_runner.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=7,
            encoding="utf-8",
        ),
    ]
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)


# EXECUTION

class DailyRunner:
    """Orchestrates daily scans, email digests, inbox polling, and trade execution."""

    def __init__(
        self,
        scan_time: str = "16:30",
        poll_interval_minutes: int = 15,
        scan_limit: int = 40,
        account_size: float = 200_000.0,
        execute_approved: bool = False,
        send_email: bool = True,
        send_sms: bool = False,
    ) -> None:
        self.scan_time = scan_time
        self.poll_interval_sec = poll_interval_minutes * 60
        self.scan_limit = scan_limit
        self.account_size = account_size
        self.execute_approved = execute_approved
        self.send_email = send_email
        self.send_sms = send_sms

        self.logger = logging.getLogger("DailyRunner")
        self._running = False
        self._last_scan_date: date | None = None
        self._last_poll_at: datetime | None = None
        self._orch: TradingOrchestrator | None = None

    # CONFIGURATION

    def _build_orchestrator(self) -> TradingOrchestrator:
        config = OrchestratorConfig(
            account_size=self.account_size,
            risk_per_trade_pct=1.0,
            max_concurrent_positions=3,
            data_period="1y",
        )
        orch = TradingOrchestrator(config=config)
        if not orch.initialize():
            raise RuntimeError("Orchestrator failed to initialize")
        if self.scan_limit:
            orch.stock_universe = orch.stock_universe[: self.scan_limit]
        return orch

    def _teardown(self) -> None:
        if self._orch:
            try:
                self._orch.shutdown()
            except Exception:
                pass
            self._orch = None

    # EXECUTION

    def _run_scan_cycle(self) -> None:
        """Scan the market, generate proposals, and send the email digest."""
        self.logger.info("=" * 64)
        self.logger.info("Daily scan starting  —  %s", datetime.now().strftime("%A, %B %d, %Y  %I:%M %p"))
        self.logger.info("=" * 64)

        # Fresh orchestrator each day so stale state never bleeds in.
        self._teardown()
        try:
            self._orch = self._build_orchestrator()
        except RuntimeError as exc:
            self.logger.error("Cannot start orchestrator: %s", exc)
            return

        try:
            proposals = self._orch.run_scan()
            n = len(proposals)
            self.logger.info("Scan finished — %d proposal(s) generated", n)

            self._orch.send_daily_proposal_digest(
                proposals,
                send_email=self.send_email,
                send_sms=self.send_sms,
            )
            if self.send_email:
                self.logger.info("HTML digest email dispatched to inbox")

            self._last_scan_date = date.today()
            # Reset poll timer so inbox checks start right away.
            self._last_poll_at = None

        except Exception as exc:
            self.logger.error("Scan cycle failed: %s", exc, exc_info=True)

    def _check_inbox(self) -> None:
        """Poll the inbox directory, process any response file found."""
        if not self._orch:
            return

        response = self._orch.notification_module.ingest_latest_response(archive=True)
        if response is None:
            self.logger.debug("Inbox poll: no response found")
            return

        self.logger.info("Response received: %r", response)
        summary = self._orch.process_user_approval_response(response)
        approved = summary.get("approved_count", 0)
        rejected = summary.get("rejected_count", 0)
        self.logger.info(
            "Approval processed — approved: %d, rejected: %d, mode: %s",
            approved, rejected, summary.get("mode"),
        )

        if self.execute_approved and approved > 0:
            self.logger.info("Executing %d approved trade(s)…", approved)
            try:
                executions = self._orch.execute_approved_trades()
                self.logger.info("Executed %d trade(s)", len(executions))
            except Exception as exc:
                self.logger.error("Execution failed: %s", exc, exc_info=True)

    # DATA

    def _is_scan_minute(self) -> bool:
        hour, minute = map(int, self.scan_time.split(":"))
        now = datetime.now()
        return now.hour == hour and now.minute == minute

    def _should_run_scan(self) -> bool:
        return self._is_scan_minute() and self._last_scan_date != date.today()

    def _should_poll(self) -> bool:
        # Only poll after today's scan has run
        if self._last_scan_date != date.today():
            return False
        if self._last_poll_at is None:
            return True
        elapsed = (datetime.now() - self._last_poll_at).total_seconds()
        return elapsed >= self.poll_interval_sec

    # EXECUTION

    def start(self, run_now: bool = False) -> None:
        self._running = True
        self.logger.info(
            "Daily Runner live — scan at %s local time — inbox poll every %d min",
            self.scan_time,
            self.poll_interval_sec // 60,
        )

        if run_now:
            self.logger.info("--run-now: launching scan immediately")
            self._run_scan_cycle()

        while self._running:
            try:
                if self._should_run_scan():
                    self._run_scan_cycle()

                if self._should_poll():
                    self._check_inbox()
                    self._last_poll_at = datetime.now()

                time.sleep(30)  # wake up every 30 s to check schedule

            except KeyboardInterrupt:
                break
            except Exception as exc:
                self.logger.error("Unexpected loop error: %s", exc, exc_info=True)
                time.sleep(30)

        self.logger.info("Shutting down…")
        self._teardown()
        self.logger.info("Daily Runner stopped.")

    def stop(self) -> None:
        self._running = False


# CONFIGURATION

def main() -> None:
    load_dotenv()
    _setup_logging()

    parser = argparse.ArgumentParser(
        description="AI Trading Scanner — Daily Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--schedule", default="16:30", metavar="HH:MM",
        help="Daily scan time in 24-hour local clock format.  Default: 16:30",
    )
    parser.add_argument(
        "--poll-interval", type=int, default=15, metavar="MINUTES",
        help="How often to check the inbox for a response (minutes).  Default: 15",
    )
    parser.add_argument(
        "--scan-limit", type=int, default=40, metavar="N",
        help="Maximum number of symbols to scan per day.  Default: 40",
    )
    parser.add_argument(
        "--account-size", type=float, default=200_000.0, metavar="USD",
        help="Account size used for position sizing.  Default: 200000",
    )
    parser.add_argument(
        "--execute-approved", action="store_true",
        help="Automatically execute approved trades (requires a configured broker).",
    )
    parser.add_argument(
        "--run-now", action="store_true",
        help="Run a scan immediately on startup, then continue on schedule.",
    )
    parser.add_argument(
        "--no-email", action="store_true",
        help="Suppress email sending (useful for local testing).",
    )
    parser.add_argument(
        "--send-sms", action="store_true",
        help="Send SMS via Twilio in addition to email.",
    )

    args = parser.parse_args()

    runner = DailyRunner(
        scan_time=args.schedule,
        poll_interval_minutes=args.poll_interval,
        scan_limit=args.scan_limit,
        account_size=args.account_size,
        execute_approved=args.execute_approved,
        send_email=not args.no_email,
        send_sms=args.send_sms,
    )

    # Graceful shutdown on Ctrl-C or SIGTERM
    def _on_signal(signum: int, frame: object) -> None:
        print("\nShutdown signal received — stopping…")
        runner.stop()

    signal.signal(signal.SIGINT, _on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _on_signal)

    runner.start(run_now=args.run_now)


if __name__ == "__main__":
    main()
