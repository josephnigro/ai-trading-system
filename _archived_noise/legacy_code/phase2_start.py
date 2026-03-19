"""Phase 2 entrypoint: scan, digest delivery, approval processing, and execution."""

import argparse
import logging
from dotenv import load_dotenv

from orchestrator import TradingOrchestrator, OrchestratorConfig, build_alpaca_broker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


# EXECUTION
def main() -> None:
    """Run the Phase 2 workflow from CLI arguments."""
    # CONFIGURATION
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run Phase 2 proposal + approval workflow")
    parser.add_argument(
        "--response",
        type=str,
        default=None,
        help="Approval response (yes/no or comma-separated selections)",
    )
    parser.add_argument(
        "--response-file",
        type=str,
        default=None,
        help="Path to response file (.txt or .json) used for approval ingestion",
    )
    parser.add_argument(
        "--response-inbox",
        type=str,
        default=None,
        help="Inbox directory for response ingestion (.txt/.json payloads)",
    )
    parser.add_argument(
        "--scan-limit",
        type=int,
        default=8,
        help="Limit number of symbols scanned for quicker runs",
    )
    parser.add_argument(
        "--execute-approved",
        action="store_true",
        help="Execute approved trades (requires broker configured)",
    )
    parser.add_argument(
        "--alpaca",
        action="store_true",
        help="Wire in AlpacaBroker for paper/live execution via Alpaca",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send digest via SMTP (requires NOTIFY_SMTP_* env config)",
    )
    parser.add_argument(
        "--send-sms",
        action="store_true",
        help="Send digest via Twilio SMS (requires NOTIFY_TWILIO_* env config)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for response if no direct/inbox response is available",
    )
    parser.add_argument(
        "--transport-status",
        action="store_true",
        help="Print SMTP/Twilio readiness and exit",
    )
    parser.add_argument(
        "--test-delivery",
        action="store_true",
        help="Send test message over selected transport flags and exit",
    )
    args = parser.parse_args()

    config = OrchestratorConfig(
        account_size=200000.0,
        risk_per_trade_pct=1.0,
        max_concurrent_positions=3,
        data_period="1y",
    )

    broker = build_alpaca_broker() if args.alpaca else None
    orchestrator = TradingOrchestrator(config=config, broker=broker)
    if not orchestrator.initialize():
        print("Initialization failed")
        return

    if args.transport_status:
        print(orchestrator.notification_module.get_transport_readiness())
        orchestrator.shutdown()
        return

    if args.test_delivery:
        outcome = orchestrator.notification_module.send_test_digest(
            send_email=args.send_email,
            send_sms=args.send_sms,
        )
        print(f"Test delivery outcome: {outcome}")
        orchestrator.shutdown()
        return

    if args.scan_limit > 0:
        orchestrator.stock_universe = orchestrator.stock_universe[:args.scan_limit]

    # OUTPUT
    response = args.response
    if response is None and args.interactive:
        print("Enter your response (yes / no / specific selection):")
        response = input("> ").strip()

    result = orchestrator.run_daily_phase2_cycle(
        user_response=response,
        response_file=args.response_file,
        response_inbox_dir=args.response_inbox,
        send_email=args.send_email,
        send_sms=args.send_sms,
        execute_approved=args.execute_approved,
    )
    print(f"Phase 2 result: {result}")

    orchestrator.shutdown()


if __name__ == "__main__":
    main()
