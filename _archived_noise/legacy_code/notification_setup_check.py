"""
Notification setup checker and test sender.

Usage:
1) Check config only:
   python notification_setup_check.py --status

2) Send test email:
   python notification_setup_check.py --send-email

3) Send test SMS:
   python notification_setup_check.py --send-sms

4) Send both:
   python notification_setup_check.py --send-email --send-sms
"""

import argparse
from dotenv import load_dotenv

from src.notification_module import NotificationModule


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Validate and test notification transports")
    parser.add_argument("--status", action="store_true", help="Print readiness status")
    parser.add_argument("--send-email", action="store_true", help="Send test email")
    parser.add_argument("--send-sms", action="store_true", help="Send test SMS")
    args = parser.parse_args()

    module = NotificationModule()

    if args.status or (not args.send_email and not args.send_sms):
        print("Transport readiness:")
        print(module.get_transport_readiness())

    if args.send_email or args.send_sms:
        outcome = module.send_test_digest(send_email=args.send_email, send_sms=args.send_sms)
        print("Test outcome:")
        print(outcome)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
