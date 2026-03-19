"""Notification delivery and approval-response ingestion."""

import json
import os
import smtplib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from email.message import EmailMessage
from typing import List, Dict, Optional

from ..core.base_module import BaseModule
from ..core.trade_proposal import TradeProposal


# CONFIGURATION


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class NotificationConfig:
    """Notification transport and ingestion configuration."""

    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from: str = ""
    email_to: str = ""

    twilio_enabled: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    twilio_to_number: str = ""

    dashboard_url: str = "http://localhost:8501"

    def __post_init__(self) -> None:
        """Load values from environment at runtime."""
        self.smtp_enabled = _env_bool("NOTIFY_SMTP_ENABLED", self.smtp_enabled)
        self.smtp_host = os.getenv("NOTIFY_SMTP_HOST", self.smtp_host)
        port_str = os.getenv("NOTIFY_SMTP_PORT", "").strip()
        try:
            self.smtp_port = int(port_str) if port_str else self.smtp_port
        except ValueError:
            pass  # Invalid value, use default
        self.smtp_username = os.getenv("NOTIFY_SMTP_USERNAME", self.smtp_username)
        self.smtp_password = os.getenv("NOTIFY_SMTP_PASSWORD", self.smtp_password)
        self.smtp_use_tls = _env_bool("NOTIFY_SMTP_USE_TLS", self.smtp_use_tls)
        self.email_from = os.getenv("NOTIFY_EMAIL_FROM", self.email_from)
        self.email_to = os.getenv("NOTIFY_EMAIL_TO", self.email_to)

        self.twilio_enabled = _env_bool("NOTIFY_TWILIO_ENABLED", self.twilio_enabled)
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", self.twilio_account_sid)
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", self.twilio_auth_token)
        self.twilio_from_number = os.getenv("TWILIO_PHONE_NUMBER", self.twilio_from_number)
        self.twilio_to_number = os.getenv("NOTIFY_SMS_TO", self.twilio_to_number)
        self.dashboard_url = os.getenv("DASHBOARD_URL", self.dashboard_url)


class NotificationModule(BaseModule):
    """
    Handles outbound proposal messaging and inbound approval parsing.
    """

    def __init__(
        self,
        out_dir: str = "logs/notifications",
        config: Optional[NotificationConfig] = None,
    ):
        super().__init__("NotificationModule")
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_dir = self.out_dir / "inbox"
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir = self.inbox_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or NotificationConfig()

    # OUTPUT
    def get_transport_readiness(self) -> Dict[str, Dict[str, str | bool]]:
        """Return readiness status for SMTP and Twilio transports."""
        smtp_ready = all([
            self.config.smtp_host,
            self.config.smtp_username,
            self.config.smtp_password,
            self.config.email_from,
            self.config.email_to,
        ])
        sms_ready = all([
            self.config.twilio_account_sid,
            self.config.twilio_auth_token,
            self.config.twilio_from_number,
            self.config.twilio_to_number,
        ])

        return {
            "smtp": {
                "enabled": self.config.smtp_enabled,
                "ready": smtp_ready,
                "host": bool(self.config.smtp_host),
                "username": bool(self.config.smtp_username),
                "password": bool(self.config.smtp_password),
                "email_from": bool(self.config.email_from),
                "email_to": bool(self.config.email_to),
            },
            "sms": {
                "enabled": self.config.twilio_enabled,
                "ready": sms_ready,
                "account_sid": bool(self.config.twilio_account_sid),
                "auth_token": bool(self.config.twilio_auth_token),
                "from_number": bool(self.config.twilio_from_number),
                "to_number": bool(self.config.twilio_to_number),
            },
        }

    def send_test_digest(self, send_email: bool = False, send_sms: bool = False) -> Dict[str, bool]:
        """Send a transport test digest without requiring scan data."""
        now = datetime.now()
        subject = f"AI Trading — Transport Test — {now.strftime('%B %d, %Y %I:%M %p')}"
        body = (
            "This is a test digest from AI Trading Scanner.\n\n"
            "If you received this, your transport setup is working correctly.\n\n"
            "How to respond to daily digests:\n"
            "  yes       - approve all trades\n"
            "  no        - reject all trades\n"
            "  1,3       - approve trades 1 and 3\n"
            "  PLTR,GME  - approve by ticker\n"
            "\n"
            "Dashboard:\n"
            f"  {self.config.dashboard_url}\n"
        )
        html_body = self._build_test_html(now)
        email_sent = self.send_email(subject, body, html_body=html_body) if send_email else False
        sms_sent = self.send_sms(body) if send_sms else False
        return {"email_sent": email_sent, "sms_sent": sms_sent}

    def _build_test_html(self, now: datetime) -> str:
        """Build a simple HTML confirmation email for transport testing."""
        date_str = now.strftime("%A, %B %d, %Y at %I:%M %p")
        return (
            "<!DOCTYPE html>\n"
            '<html xmlns="http://www.w3.org/1999/xhtml"><head>'
            '<meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
            "</head>"
            '<body style="margin:0;padding:0;background-color:#f0f2f5;font-family:Arial,sans-serif;">'
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f0f2f5">'
            '<tr><td align="center" style="padding:24px 0;">'
            '<table width="560" cellpadding="0" cellspacing="0" border="0">'
            '<tr><td bgcolor="#0d1b2a" style="padding:28px 32px;text-align:center;border-radius:8px 8px 0 0;">'
            '<p style="font-family:Arial,sans-serif;font-size:11px;color:#64b5f6;margin:0 0 6px;'
            'letter-spacing:2px;text-transform:uppercase;">AI Trading Scanner</p>'
            '<h1 style="font-family:Arial,sans-serif;font-size:22px;color:#ffffff;margin:0 0 8px;">'
            'Transport Test</h1>'
            f'<p style="font-family:Arial,sans-serif;font-size:13px;color:#b0bec5;margin:0;">{date_str}</p>'
            '</td></tr>'
            '<tr><td bgcolor="#ffffff" style="padding:28px 32px;">'
            '<p style="font-family:Arial,sans-serif;font-size:16px;color:#0d1b2a;font-weight:bold;margin:0 0 12px;">'
            'Your email delivery is working!</p>'
            '<p style="font-family:Arial,sans-serif;font-size:14px;color:#546e7a;margin:0 0 20px;">'
            'You will receive a message like this every trading day with real trade setups.</p>'
            '<p style="font-family:Arial,sans-serif;font-size:13px;color:#37474f;font-weight:bold;margin:0 0 8px;">'
            'How to respond to daily digests:</p>'
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">'
            '<tr bgcolor="#f5f5f5"><td style="padding:7px 12px;border:1px solid #e0e0e0;font-family:monospace;font-weight:bold;color:#1565c0;width:100px;">yes</td>'
            '<td style="padding:7px 12px;border:1px solid #e0e0e0;font-size:13px;color:#37474f;">Approve ALL trades</td></tr>'
            '<tr><td style="padding:7px 12px;border:1px solid #e0e0e0;font-family:monospace;font-weight:bold;color:#c62828;">no</td>'
            '<td style="padding:7px 12px;border:1px solid #e0e0e0;font-size:13px;color:#37474f;">Reject ALL trades</td></tr>'
            '<tr bgcolor="#f5f5f5"><td style="padding:7px 12px;border:1px solid #e0e0e0;font-family:monospace;font-weight:bold;color:#1565c0;">1,3</td>'
            '<td style="padding:7px 12px;border:1px solid #e0e0e0;font-size:13px;color:#37474f;">Approve trades #1 and #3</td></tr>'
            '<tr><td style="padding:7px 12px;border:1px solid #e0e0e0;font-family:monospace;font-weight:bold;color:#1565c0;">PLTR,GME</td>'
            '<td style="padding:7px 12px;border:1px solid #e0e0e0;font-size:13px;color:#37474f;">Approve by ticker</td></tr>'
            '</table>'
            '<p style="font-family:Arial,sans-serif;font-size:13px;color:#37474f;font-weight:bold;margin:16px 0 6px;">'
            'Live dashboard:</p>'
            f'<p style="margin:0;"><a href="{self.config.dashboard_url}" '
            'style="font-family:Arial,sans-serif;font-size:14px;color:#1565c0;font-weight:bold;">'
            f'{self.config.dashboard_url}</a></p>'
            '</td></tr>'
            '<tr><td bgcolor="#0d1b2a" style="padding:12px 32px;text-align:center;border-radius:0 0 8px 8px;">'
            '<p style="font-family:Arial,sans-serif;font-size:11px;color:#546e7a;margin:0;">'
            'AI Trading Scanner &#x00B7; Automated Market Analysis</p>'
            '</td></tr></table></td></tr></table></body></html>'
        )

    # SIGNALS
    def build_trade_digest(self, proposals: List[TradeProposal]) -> str:
        """
        Build the plain-text daily proposal digest (used for SMS + email fallback).
        """
        header = "AI Trading Scanner — Daily Report"
        if not proposals:
            return (
                f"{header}\n\n"
                "No qualified proposals were found in today's scan.\n\n"
                "DASHBOARD:\n"
                f"  Open live dashboard: {self.config.dashboard_url}"
            )

        lines = [header, "", f"Found {len(proposals)} trade setup(s) today:", "", "─" * 50]
        for idx, proposal in enumerate(proposals, start=1):
            signal = proposal.signal
            if signal is None:
                continue
            profit_pct = signal.potential_profit_pct
            loss_pct = abs(signal.potential_loss_pct)
            rr = signal.reward_to_risk
            lines.extend([
                f"",
                f"#{idx}  {signal.signal_type.value} {signal.ticker}  |  Confidence: {signal.overall_confidence:.0f}%",
                f"    Entry:   ${signal.entry_price:.2f}",
                f"    Target:  ${signal.profit_target:.2f}  (+{profit_pct:.1f}%)",
                f"    Stop:    ${signal.stop_loss:.2f}  (-{loss_pct:.1f}%)",
                f"    R/R:     1:{rr:.2f}  |  Risk: ${proposal.risk_amount:.2f}",
                f"    Size:    {proposal.shares} shares  ({proposal.position_size_pct:.1f}% of account)",
            ])
            if signal.reason:
                lines.append(f"    Why:     {signal.reason}")

        lines.extend([
            "", "─" * 50, "",
            "HOW TO APPROVE:",
            "  yes        — approve all trades",
            "  no         — reject all trades",
            "  1,3        — approve by number",
            "  PLTR,GME   — approve by ticker",
            "",
            f"Drop a file in: logs/notifications/inbox/approval.txt",
            "",
            "DASHBOARD:",
            f"  Open live dashboard: {self.config.dashboard_url}",
        ])
        return "\n".join(lines)

    def build_html_digest(
        self,
        proposals: List[TradeProposal],
        performance_html: Optional[str] = None,
    ) -> str:
        """Build a rich HTML email for the daily proposal digest."""
        now = datetime.now()
        scan_date = now.strftime("%A, %B %d, %Y")
        scan_time = now.strftime("%I:%M %p")
        valid = [p for p in proposals if p.signal is not None]
        n = len(valid)
        n_label = "opportunity" if n == 1 else "opportunities"
        n_text = f"{n} trade" + ("" if n == 1 else "s")

        # ── Build individual trade cards ──────────────────────────────────────
        trade_cards: List[str] = []
        for idx, proposal in enumerate(valid, start=1):
            sig = proposal.signal
            is_long = sig.signal_type.value in ("BUY", "COVER")
            badge_bg = "#43a047" if is_long else "#e53935"
            border_col = "#43a047" if is_long else "#e53935"
            profit_pct = sig.potential_profit_pct
            loss_pct = abs(sig.potential_loss_pct)
            rr = sig.reward_to_risk
            conf = sig.overall_confidence
            conf_color = "#43a047" if conf >= 75 else ("#fb8c00" if conf >= 55 else "#e53935")
            conf_bar = int(min(conf, 100))
            reason = sig.reason or "Technical analysis signal"
            position_cost = proposal.shares * sig.entry_price
            trade_cards.append(
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0"'
                f' style="margin-bottom:16px;border:1px solid #e0e0e0;border-left:5px solid {border_col};border-radius:6px;">'
                f'<tr bgcolor="#ffffff"><td style="padding:14px 16px;">'
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                f'<td><span style="font-family:Arial,sans-serif;font-size:22px;font-weight:bold;color:#0d1b2a;">{sig.ticker}</span>'
                f'&nbsp;<span style="font-family:Arial,sans-serif;font-size:12px;font-weight:bold;'
                f'background-color:{badge_bg};color:#ffffff;padding:3px 10px;border-radius:12px;">{sig.signal_type.value}</span>'
                f'&nbsp;<span style="font-family:Arial,sans-serif;font-size:13px;color:#90a4ae;">#{idx}</span></td>'
                f'<td align="right"><span style="font-family:Arial,sans-serif;font-size:18px;font-weight:bold;color:#0d1b2a;">${sig.entry_price:.2f}</span>'
                f'<span style="font-family:Arial,sans-serif;font-size:12px;color:#90a4ae;"> entry</span></td>'
                f'</tr></table></td></tr>'
                f'<tr bgcolor="#ffffff"><td style="padding:2px 16px 10px;">'
                f'<p style="font-family:Arial,sans-serif;font-size:11px;color:#90a4ae;margin:0 0 3px;">'
                f'AI Confidence: <strong style="color:{conf_color};">{conf:.0f}%</strong></p>'
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#eceff1;border-radius:3px;height:6px;">'
                f'<tr><td width="{conf_bar}%" bgcolor="{conf_color}" style="height:6px;border-radius:3px;"></td><td></td></tr>'
                f'</table></td></tr>'
                f'<tr><td style="height:1px;background-color:#eceff1;"></td></tr>'
                f'<tr bgcolor="#fafafa"><td style="padding:10px 16px;">'
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0">'
                f'<tr><td style="font-family:Arial,sans-serif;font-size:13px;color:#546e7a;padding:3px 0;">Target</td>'
                f'<td align="right" style="font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#43a047;padding:3px 0;">'
                f'${sig.profit_target:.2f} <span style="font-size:11px;font-weight:normal;color:#81c784;">(+{profit_pct:.1f}%)</span></td></tr>'
                f'<tr><td style="font-family:Arial,sans-serif;font-size:13px;color:#546e7a;padding:3px 0;">Stop Loss</td>'
                f'<td align="right" style="font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#e53935;padding:3px 0;">'
                f'${sig.stop_loss:.2f} <span style="font-size:11px;font-weight:normal;color:#ef9a9a;">(-{loss_pct:.1f}%)</span></td></tr>'
                f'<tr><td style="font-family:Arial,sans-serif;font-size:13px;color:#546e7a;padding:3px 0;">Risk / Reward</td>'
                f'<td align="right" style="font-family:Arial,sans-serif;font-size:13px;font-weight:bold;color:#1565c0;padding:3px 0;">1&thinsp;:&thinsp;{rr:.2f}</td></tr>'
                f'</table></td></tr>'
                f'<tr><td style="height:1px;background-color:#eceff1;"></td></tr>'
                f'<tr bgcolor="#f5f5f5"><td style="padding:10px 16px;">'
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0">'
                f'<tr><td style="font-family:Arial,sans-serif;font-size:13px;color:#546e7a;padding:2px 0;">Position</td>'
                f'<td align="right" style="font-family:Arial,sans-serif;font-size:13px;color:#37474f;padding:2px 0;">'
                f'{proposal.shares}&nbsp;shares &middot; ${position_cost:,.0f} &middot; {proposal.position_size_pct:.1f}% of account</td></tr>'
                f'<tr><td style="font-family:Arial,sans-serif;font-size:13px;color:#546e7a;padding:2px 0;">Max Risk</td>'
                f'<td align="right" style="font-family:Arial,sans-serif;font-size:13px;color:#e53935;font-weight:bold;padding:2px 0;">${proposal.risk_amount:.2f}</td></tr>'
                f'</table></td></tr>'
                f'<tr><td style="height:1px;background-color:#eceff1;"></td></tr>'
                f'<tr bgcolor="#fafafa"><td style="padding:8px 16px;font-family:Arial,sans-serif;font-size:12px;color:#90a4ae;font-style:italic;">{reason}</td></tr>'
                f'</table>'
            )

        # ── Trades section content ────────────────────────────────────────────
        if n == 0:
            trades_inner = (
                '<p style="font-family:Arial,sans-serif;font-size:15px;color:#78909c;text-align:center;padding:32px 0;">'
                'No qualifying trade setups found today. The scanner will run again tomorrow.</p>'
            )
        else:
            trades_inner = (
                '<h2 style="font-family:Arial,sans-serif;font-size:13px;color:#78909c;margin:0 0 16px;'
                'text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #e0e0e0;padding-bottom:8px;">'
                "Today&#x2019;s Trade Setups</h2>"
                + "".join(trade_cards)
            )

        # ── Reply instructions ────────────────────────────────────────────────
        inbox_path = str(self.inbox_dir)
        reply_inner = (
            '<h3 style="font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#0d47a1;margin:0 0 10px;">'
            'How to Approve Trades</h3>'
            '<p style="font-family:Arial,sans-serif;font-size:13px;color:#37474f;margin:0 0 12px;">'
            'Drop a response file in the inbox folder. Responses are checked every 15 minutes.</p>'
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">'
            f'<tr bgcolor="#ffffff"><td style="padding:7px 12px;border:1px solid #bbdefb;font-family:monospace;font-weight:bold;font-size:13px;color:#1565c0;width:110px;">yes</td>'
            f'<td style="padding:7px 12px;border:1px solid #bbdefb;font-family:Arial,sans-serif;font-size:13px;color:#37474f;">Approve ALL {n_text}</td></tr>'
            '<tr bgcolor="#fafafa"><td style="padding:7px 12px;border:1px solid #bbdefb;font-family:monospace;font-weight:bold;font-size:13px;color:#c62828;">no</td>'
            '<td style="padding:7px 12px;border:1px solid #bbdefb;font-family:Arial,sans-serif;font-size:13px;color:#37474f;">Reject ALL trades</td></tr>'
            '<tr bgcolor="#ffffff"><td style="padding:7px 12px;border:1px solid #bbdefb;font-family:monospace;font-weight:bold;font-size:13px;color:#1565c0;">1,3</td>'
            '<td style="padding:7px 12px;border:1px solid #bbdefb;font-family:Arial,sans-serif;font-size:13px;color:#37474f;">Approve trades #1 and #3 (by number)</td></tr>'
            '<tr bgcolor="#fafafa"><td style="padding:7px 12px;border:1px solid #bbdefb;font-family:monospace;font-weight:bold;font-size:13px;color:#1565c0;">PLTR,GME</td>'
            '<td style="padding:7px 12px;border:1px solid #bbdefb;font-family:Arial,sans-serif;font-size:13px;color:#37474f;">Approve by ticker symbol</td></tr>'
            '</table>'
            f'<p style="font-family:Arial,sans-serif;font-size:12px;color:#78909c;margin:14px 0 0;">'
            f'Inbox folder: <code style="background:#e3f2fd;padding:2px 6px;border-radius:3px;">{inbox_path}</code></p>'
        )

        dashboard_url = self.config.dashboard_url
        dashboard_inner = (
            '<h3 style="font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#0d47a1;margin:0 0 10px;">'
            'Live Dashboard</h3>'
            '<p style="font-family:Arial,sans-serif;font-size:13px;color:#37474f;margin:0 0 12px;">'
            'View positions, performance, backtests, and submit approvals from the dashboard:</p>'
            f'<p style="margin:0;">'
            f'<a href="{dashboard_url}" style="font-family:Arial,sans-serif;font-size:14px;color:#1565c0;font-weight:bold;">'
            f'{dashboard_url}</a></p>'
        )

        performance_block = ""
        if performance_html:
            performance_block = (
                f'<tr><td bgcolor="#ffffff" style="padding:0 32px 16px;">{performance_html}</td></tr>\n'
            )

        # ── Assemble full HTML ────────────────────────────────────────────────
        return (
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            '<head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
            '<title>AI Trading Scanner</title></head>\n'
            '<body style="margin:0;padding:0;background-color:#f0f2f5;">\n'
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f0f2f5">\n'
            '<tr><td align="center" style="padding:24px 0;">\n'
            '<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">\n'
            f'<tr><td bgcolor="#0d1b2a" style="padding:28px 32px;text-align:center;border-radius:8px 8px 0 0;">'
            '<p style="font-family:Arial,sans-serif;font-size:11px;color:#64b5f6;margin:0 0 6px;letter-spacing:2px;text-transform:uppercase;">AI Trading Scanner</p>'
            '<h1 style="font-family:Arial,sans-serif;font-size:24px;color:#ffffff;margin:0 0 8px;">Daily Market Report</h1>'
            f'<p style="font-family:Arial,sans-serif;font-size:13px;color:#b0bec5;margin:0;">{scan_date} &middot; Completed at {scan_time}</p>'
            '</td></tr>\n'
            f'<tr><td bgcolor="#1a2a3a" style="padding:12px 32px;text-align:center;border-bottom:3px solid #00bcd4;">'
            f'<p style="font-family:Arial,sans-serif;font-size:15px;color:#ffffff;margin:0;">'
            f'Found <strong style="color:#00e5ff;">{n}</strong> trade {n_label} today</p>'
            '</td></tr>\n'
            f'<tr><td bgcolor="#ffffff" style="padding:24px 32px 8px;">{trades_inner}</td></tr>\n'
            + performance_block +
            f'<tr><td bgcolor="#e8f4fd" style="padding:24px 32px 12px;">{reply_inner}</td></tr>\n'
            f'<tr><td bgcolor="#e8f4fd" style="padding:0 32px 24px;">{dashboard_inner}</td></tr>\n'
            f'<tr><td bgcolor="#0d1b2a" style="padding:14px 32px;text-align:center;border-radius:0 0 8px 8px;">'
            f'<p style="font-family:Arial,sans-serif;font-size:11px;color:#546e7a;margin:0;">'
            f'AI Trading Scanner &middot; Automated Market Analysis &middot; {scan_date}</p>'
            '<p style="font-family:Arial,sans-serif;font-size:10px;color:#37474f;margin:4px 0 0;">'
            'All trade decisions require your approval before execution.</p>'
            '</td></tr>\n'
            '</table>\n'
            '</td></tr></table>\n'
            '</body></html>\n'
        )

    # OUTPUT
    def publish_trade_digest(
        self,
        proposals: List[TradeProposal],
        send_email: bool = False,
        send_sms: bool = False,
        performance_html: Optional[str] = None,
    ) -> str:
        """
        Save and print digest message for user review.
        Sends an HTML email (with plain-text fallback) and optional SMS.
        """
        message = self.build_trade_digest(proposals)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = self.out_dir / f"daily_digest_{ts}.txt"
        out_file.write_text(message, encoding="utf-8")

        now = datetime.now()
        n = len([p for p in proposals if p.signal is not None])
        setup_word = "Setup" if n == 1 else "Setups"
        subject = (
            f"AI Trading \u2014 {n} Trade {setup_word} Found \u2014 {now.strftime('%B %d, %Y')}"
            if n > 0
            else f"AI Trading \u2014 No Setups Today \u2014 {now.strftime('%B %d, %Y')}"
        )
        if send_email:
            html_body = self.build_html_digest(proposals, performance_html=performance_html)
            self.send_email(subject, message, html_body=html_body)
        if send_sms:
            self.send_sms(message)

        print("\n" + "=" * 80)
        print("DAILY TRADE DIGEST")
        print("=" * 80)
        print(message)
        print("=" * 80 + "\n")

        return message

    # EXECUTION
    def send_email(self, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send digest via SMTP.  Attaches HTML alternative when html_body is supplied."""
        if not self.config.smtp_enabled:
            self.logger.info("SMTP send skipped: NOTIFY_SMTP_ENABLED is false")
            return False

        required = [
            self.config.smtp_host,
            self.config.smtp_username,
            self.config.smtp_password,
            self.config.email_from,
            self.config.email_to,
        ]
        if not all(required):
            self.log_error("SMTP send skipped: missing SMTP config values")
            return False

        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.config.email_from
            msg["To"] = self.config.email_to
            msg.set_content(body)
            if html_body:
                msg.add_alternative(html_body, subtype="html")

            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=30) as server:
                if self.config.smtp_use_tls:
                    server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)

            self.logger.info("SMTP digest sent successfully")
            return True
        except Exception as exc:
            self.log_error(f"SMTP send failed: {exc}")
            return False

    def send_sms(self, body: str) -> bool:
        """Send digest via Twilio SMS."""
        if not self.config.twilio_enabled:
            self.logger.info("SMS send skipped: NOTIFY_TWILIO_ENABLED is false")
            return False

        required = [
            self.config.twilio_account_sid,
            self.config.twilio_auth_token,
            self.config.twilio_from_number,
            self.config.twilio_to_number,
        ]
        if not all(required):
            self.log_error("SMS send skipped: missing Twilio config values")
            return False

        try:
            from twilio.rest import Client  # type: ignore

            sms_text = body[:1500]
            client = Client(self.config.twilio_account_sid, self.config.twilio_auth_token)
            client.messages.create(
                body=sms_text,
                from_=self.config.twilio_from_number,
                to=self.config.twilio_to_number,
            )
            self.logger.info("Twilio SMS sent successfully")
            return True
        except ImportError:
            self.log_error("SMS send failed: twilio package not installed")
            return False
        except Exception as exc:
            self.log_error(f"SMS send failed: {exc}")
            return False

    # DATA
    def ingest_response_from_file(self, response_file: str) -> Optional[str]:
        """
        Ingest one user response from a file.
        Supports .txt or .json payloads.
        """
        file_path = Path(response_file)
        if not file_path.exists():
            self.log_error(f"Response file not found: {file_path}")
            return None

        try:
            raw = file_path.read_text(encoding="utf-8").strip()
            if not raw:
                return None

            if file_path.suffix.lower() == ".json":
                data = json.loads(raw)
                for key in ("response", "message", "body", "text"):
                    value = data.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                return None

            return raw.splitlines()[0].strip()
        except Exception as exc:
            self.log_error(f"Failed reading response file: {exc}")
            return None

    def ingest_latest_response(self, inbox_dir: Optional[str] = None, archive: bool = True) -> Optional[str]:
        """
        Ingest latest response payload from inbox directory.
        Supported file types: .txt, .json
        """
        target_dir = Path(inbox_dir) if inbox_dir else self.inbox_dir
        if not target_dir.exists():
            return None

        files = [
            path for path in target_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".txt", ".json"}
        ]
        if not files:
            return None

        latest = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        response = self.ingest_response_from_file(str(latest))

        if archive:
            archived = self.processed_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{latest.name}"
            latest.rename(archived)

        return response

    def get_ingested_response(
        self,
        direct_response: Optional[str] = None,
        response_file: Optional[str] = None,
        response_inbox_dir: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve response from direct value, file, or inbox directory."""
        if direct_response is not None and direct_response.strip():
            return direct_response.strip()

        if response_file:
            return self.ingest_response_from_file(response_file)

        return self.ingest_latest_response(response_inbox_dir)

    # FILTERS
    def parse_user_response(self, response: str, proposals: List[TradeProposal]) -> Dict[str, List[str] | str]:
        """
        Parse user response into approve/reject decisions.
        """
        normalized = (response or "").strip().lower()
        all_ids = [proposal.trade_id for proposal in proposals]

        if normalized in {"yes", "y", "approve all", "all"}:
            return {
                "mode": "approve_all",
                "approved_ids": all_ids,
                "rejected_ids": [],
                "invalid_tokens": [],
            }

        if normalized in {"no", "n", "reject all", "none"}:
            return {
                "mode": "reject_all",
                "approved_ids": [],
                "rejected_ids": all_ids,
                "invalid_tokens": [],
            }

        token_map: Dict[str, str] = {}
        for idx, proposal in enumerate(proposals, start=1):
            token_map[str(idx)] = proposal.trade_id
            token_map[proposal.trade_id.lower()] = proposal.trade_id
            if proposal.signal:
                token_map[proposal.signal.ticker.lower()] = proposal.trade_id

        raw_tokens = [tok.strip().lower() for tok in response.replace(";", ",").split(",") if tok.strip()]
        approved_ids: List[str] = []
        invalid_tokens: List[str] = []

        for token in raw_tokens:
            trade_id = token_map.get(token)
            if not trade_id:
                invalid_tokens.append(token)
                continue
            if trade_id not in approved_ids:
                approved_ids.append(trade_id)

        rejected_ids = [trade_id for trade_id in all_ids if trade_id not in approved_ids]

        return {
            "mode": "selective",
            "approved_ids": approved_ids,
            "rejected_ids": rejected_ids,
            "invalid_tokens": invalid_tokens,
        }

    # RISK
    def send_position_alerts(
        self,
        alerts: list,
        send_email: bool = True,
        send_sms: bool = False,
    ) -> Dict[str, bool]:
        """
        Send email/SMS alerts for positions that hit stops or targets.

        Args:
            alerts: List of PositionAlert objects (or dicts with the same keys)
        """
        if not alerts:
            return {"email_sent": False, "sms_sent": False}

        now = datetime.now()
        n = len(alerts)
        subject = f"AI Trading \u2014 Position Alert: {n} Action{'s' if n != 1 else ''} Needed \u2014 {now.strftime('%B %d, %Y %I:%M %p')}"

        # ── Plain-text ─────────────────────────────────────────────────────────
        lines = [
            "AI Trading Scanner — Position Alerts",
            "",
            f"{n} position(s) require your attention ({now.strftime('%I:%M %p %B %d, %Y')})",
            "",
        ]
        for a in alerts:
            d = a.to_dict() if hasattr(a, "to_dict") else a
            atype = d.get("alert_type", "?").replace("_", " ").upper()
            closed_note = " [AUTO-CLOSED]" if d.get("auto_closed") else ""
            lines += [
                f"  {d.get('ticker','?')} — {atype}{closed_note}",
                f"    Current Price: ${d.get('current_price', 0):.2f}",
                f"    Trigger Level: ${d.get('trigger_price', 0):.2f}",
                f"    Entry Price:   ${d.get('entry_price', 0):.2f}",
                f"    Shares:        {d.get('shares', 0)}",
                f"    Unrealized P&L: ${d.get('unrealized_pl', 0):+.2f} ({d.get('unrealized_pct', 0):+.1f}%)",
                "",
            ]

        plain_body = "\n".join(lines)
        html_body = self._build_position_alerts_html(alerts, now)

        email_sent = self.send_email(subject, plain_body, html_body=html_body) if send_email else False
        sms_lines = [
            f"AI Trading ALERT: {len(alerts)} position(s) hit stop/target."
        ]
        for a in alerts[:3]:
            d = a.to_dict() if hasattr(a, "to_dict") else a
            sms_lines.append(
                f"{d.get('ticker','?')} {d.get('alert_type','').replace('_',' ').upper()} "
                f"@ ${d.get('current_price',0):.2f}"
            )
        sms_sent = self.send_sms("\n".join(sms_lines)) if send_sms else False
        return {"email_sent": email_sent, "sms_sent": sms_sent}

    def _build_position_alerts_html(self, alerts: list, now: datetime) -> str:
        """Build HTML email for position stop/target alerts."""
        n = len(alerts)
        date_str = now.strftime("%A, %B %d, %Y at %I:%M %p")

        _TYPE_COLOR = {
            "stop_hit": ("#c62828", "#ffebee", "STOP HIT"),
            "target_hit": ("#2e7d32", "#e8f5e9", "TARGET HIT"),
            "near_stop": ("#e65100", "#fff3e0", "NEAR STOP"),
            "near_target": ("#1565c0", "#e3f2fd", "NEAR TARGET"),
        }

        cards = ""
        for a in alerts:
            d = a.to_dict() if hasattr(a, "to_dict") else a
            atype = d.get("alert_type", "near_stop")
            color, bg, label = _TYPE_COLOR.get(atype, ("#546e7a", "#f5f5f5", atype.upper()))
            closed_badge = (
                '&nbsp;<span style="background:#1b5e20;color:#fff;font-size:11px;padding:2px 8px;border-radius:10px;">AUTO-CLOSED</span>'
                if d.get("auto_closed") else ""
            )
            pl = d.get("unrealized_pl", 0.0)
            pl_pct = d.get("unrealized_pct", 0.0)
            pl_color = "#2e7d32" if pl >= 0 else "#c62828"
            cards += (
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
                f'style="margin-bottom:14px;border:1px solid {color};border-left:6px solid {color};border-radius:6px;">'
                f'<tr bgcolor="{bg}"><td style="padding:12px 16px;">'
                f'<p style="margin:0;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;color:{color};">'
                f'{label}{closed_badge}</p>'
                f'<p style="margin:4px 0 0;font-family:Arial,sans-serif;font-size:20px;font-weight:bold;color:#0d1b2a;">'
                f'{d.get("ticker","?")} '
                f'<span style="font-size:14px;color:#546e7a;font-weight:normal;">'
                f'@ <strong>${d.get("current_price",0):.2f}</strong> '
                f'(trigger: ${d.get("trigger_price",0):.2f})</span></p>'
                f'</td></tr>'
                f'<tr bgcolor="#ffffff"><td style="padding:10px 16px;">'
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0">'
                f'<tr>'
                f'<td style="font-family:Arial,sans-serif;font-size:13px;color:#546e7a;padding:3px 0;">Entry Price</td>'
                f'<td align="right" style="font-family:Arial,sans-serif;font-size:13px;color:#37474f;padding:3px 0;">${d.get("entry_price",0):.2f}</td>'
                f'</tr><tr>'
                f'<td style="font-family:Arial,sans-serif;font-size:13px;color:#546e7a;padding:3px 0;">Shares</td>'
                f'<td align="right" style="font-family:Arial,sans-serif;font-size:13px;color:#37474f;padding:3px 0;">{d.get("shares",0)}</td>'
                f'</tr><tr>'
                f'<td style="font-family:Arial,sans-serif;font-size:13px;color:#546e7a;padding:3px 0;">Unrealized P&amp;L</td>'
                f'<td align="right" style="font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:{pl_color};padding:3px 0;">'
                f'${pl:+.2f} ({pl_pct:+.1f}%)</td>'
                f'</tr>'
                f'</table></td></tr>'
                f'</table>'
            )

        return (
            '<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml"><head>'
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
            '</head><body style="margin:0;padding:0;background-color:#f0f2f5;">'
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f0f2f5">'
            '<tr><td align="center" style="padding:24px 0;">'
            '<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">'
            '<tr><td bgcolor="#0d1b2a" style="padding:28px 32px;text-align:center;border-radius:8px 8px 0 0;">'
            '<p style="font-family:Arial,sans-serif;font-size:11px;color:#64b5f6;margin:0 0 6px;'
            'letter-spacing:2px;text-transform:uppercase;">AI Trading Scanner</p>'
            f'<h1 style="font-family:Arial,sans-serif;font-size:22px;color:#ffffff;margin:0 0 8px;">Position Alert</h1>'
            f'<p style="font-family:Arial,sans-serif;font-size:13px;color:#b0bec5;margin:0;">{date_str}</p>'
            '</td></tr>'
            '<tr><td bgcolor="#b71c1c" style="padding:12px 32px;text-align:center;border-bottom:3px solid #ef9a9a;">'
            f'<p style="font-family:Arial,sans-serif;font-size:15px;color:#ffffff;margin:0;">'
            f'<strong style="color:#ffcdd2;">{n}</strong> position{"s require" if n != 1 else " requires"} your attention</p>'
            '</td></tr>'
            f'<tr><td bgcolor="#ffffff" style="padding:24px 32px;">{cards}</td></tr>'
            '<tr><td bgcolor="#0d1b2a" style="padding:14px 32px;text-align:center;border-radius:0 0 8px 8px;">'
            '<p style="font-family:Arial,sans-serif;font-size:11px;color:#546e7a;margin:0;">'
            f'AI Trading Scanner &middot; Position Monitor &middot; {now.strftime("%B %d, %Y")}</p>'
            f'<p style="font-family:Arial,sans-serif;font-size:10px;color:#37474f;margin:4px 0 0;">'
            f'Review your positions in your brokerage account immediately.</p>'
            '</td></tr>'
            '</table></td></tr></table></body></html>\n'
        )

    # EXECUTION
    def send_execution_confirmation(
        self,
        executions: List[Dict],
        send_email: bool = True,
        send_sms: bool = False,
    ) -> Dict[str, bool]:
        """
        Send a confirmation email/SMS after trades are executed.

        Args:
            executions: List of execution result dicts with keys:
                        ticker, shares, execution_price, order_id, trade_id
            send_email: Send email confirmation
            send_sms:   Send SMS confirmation
        """
        now = datetime.now()
        n = len(executions)
        subject = (
            f"AI Trading \u2014 {n} Trade{'s' if n != 1 else ''} Executed \u2014 {now.strftime('%B %d, %Y')}"
        )

        # ── Plain-text body ───────────────────────────────────────────────────
        lines = [
            "AI Trading Scanner — Execution Confirmation",
            "",
            f"Executed {n} trade{'s' if n != 1 else ''} at {now.strftime('%I:%M %p on %B %d, %Y')}",
            "",
        ]
        total_cost = 0.0
        for i, ex in enumerate(executions, 1):
            cost = ex.get("shares", 0) * ex.get("execution_price", 0.0)
            total_cost += cost
            lines.extend([
                f"#{i}  {ex.get('ticker', '?')}",
                f"    Shares:     {ex.get('shares', '?')}",
                f"    Exec Price: ${ex.get('execution_price', 0.0):.2f}",
                f"    Cost:       ${cost:,.2f}",
                f"    Order ID:   {ex.get('order_id', 'N/A')}",
                "",
            ])
        lines += [
            f"Total invested: ${total_cost:,.2f}",
            "",
            "Your positions are now live. Monitor them in your brokerage account.",
        ]
        plain_body = "\n".join(lines)

        html_body = self._build_execution_confirmation_html(executions, now)
        email_sent = self.send_email(subject, plain_body, html_body=html_body) if send_email else False
        sms_body = f"AI Trading: {n} trade{'s' if n != 1 else ''} executed. Total: ${total_cost:,.0f}. Check email for details."
        sms_sent = self.send_sms(sms_body) if send_sms else False
        return {"email_sent": email_sent, "sms_sent": sms_sent}

    def _build_execution_confirmation_html(self, executions: List[Dict], now: datetime) -> str:
        """Build HTML execution confirmation email."""
        n = len(executions)
        date_str = now.strftime("%A, %B %d, %Y at %I:%M %p")

        rows = ""
        total_cost = 0.0
        for i, ex in enumerate(executions, 1):
            cost = ex.get("shares", 0) * ex.get("execution_price", 0.0)
            total_cost += cost
            bg = "#ffffff" if i % 2 == 1 else "#fafafa"
            rows += (
                f'<tr bgcolor="{bg}">'
                f'<td style="padding:10px 14px;font-family:Arial,sans-serif;font-size:14px;'
                f'font-weight:bold;color:#0d1b2a;border-bottom:1px solid #eceff1;">#{i} {ex.get("ticker","?")}</td>'
                f'<td style="padding:10px 14px;font-family:Arial,sans-serif;font-size:14px;'
                f'color:#37474f;border-bottom:1px solid #eceff1;text-align:right;">{ex.get("shares","?")} shares</td>'
                f'<td style="padding:10px 14px;font-family:Arial,sans-serif;font-size:14px;'
                f'color:#37474f;border-bottom:1px solid #eceff1;text-align:right;">${ex.get("execution_price",0.0):.2f}</td>'
                f'<td style="padding:10px 14px;font-family:Arial,sans-serif;font-size:14px;'
                f'font-weight:bold;color:#0d47a1;border-bottom:1px solid #eceff1;text-align:right;">${cost:,.2f}</td>'
                f'<td style="padding:10px 14px;font-family:Arial,sans-serif;font-size:11px;'
                f'color:#90a4ae;border-bottom:1px solid #eceff1;">{ex.get("order_id","N/A")}</td>'
                f'</tr>'
            )

        return (
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml"><head>'
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
            '</head>'
            '<body style="margin:0;padding:0;background-color:#f0f2f5;font-family:Arial,sans-serif;">'
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f0f2f5">'
            '<tr><td align="center" style="padding:24px 0;">'
            '<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">'
            # Header
            '<tr><td bgcolor="#0d1b2a" style="padding:28px 32px;text-align:center;border-radius:8px 8px 0 0;">'
            '<p style="font-family:Arial,sans-serif;font-size:11px;color:#64b5f6;margin:0 0 6px;'
            'letter-spacing:2px;text-transform:uppercase;">AI Trading Scanner</p>'
            '<h1 style="font-family:Arial,sans-serif;font-size:24px;color:#ffffff;margin:0 0 8px;">'
            f'{"Trade Executed" if n == 1 else f"{n} Trades Executed"}</h1>'
            f'<p style="font-family:Arial,sans-serif;font-size:13px;color:#b0bec5;margin:0;">{date_str}</p>'
            '</td></tr>'
            # Banner
            '<tr><td bgcolor="#1b5e20" style="padding:12px 32px;text-align:center;border-bottom:3px solid #66bb6a;">'
            '<p style="font-family:Arial,sans-serif;font-size:15px;color:#ffffff;margin:0;">'
            f'<strong style="color:#a5d6a7;">{n}</strong> position{"s are" if n != 1 else " is"} now live &mdash; '
            f'Total deployed: <strong style="color:#a5d6a7;">${total_cost:,.0f}</strong></p>'
            '</td></tr>'
            # Table
            '<tr><td bgcolor="#ffffff" style="padding:24px 32px;">'
            '<h2 style="font-family:Arial,sans-serif;font-size:13px;color:#78909c;margin:0 0 16px;'
            'text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #e0e0e0;padding-bottom:8px;">'
            'Execution Summary</h2>'
            '<table width="100%" cellpadding="0" cellspacing="0" border="1" '
            'style="border-collapse:collapse;border-color:#e0e0e0;">'
            '<tr bgcolor="#e8eaf6">'
            '<th style="padding:8px 14px;font-family:Arial,sans-serif;font-size:12px;'
            'color:#3949ab;text-align:left;border-bottom:2px solid #c5cae9;">Trade</th>'
            '<th style="padding:8px 14px;font-family:Arial,sans-serif;font-size:12px;'
            'color:#3949ab;text-align:right;border-bottom:2px solid #c5cae9;">Shares</th>'
            '<th style="padding:8px 14px;font-family:Arial,sans-serif;font-size:12px;'
            'color:#3949ab;text-align:right;border-bottom:2px solid #c5cae9;">Fill Price</th>'
            '<th style="padding:8px 14px;font-family:Arial,sans-serif;font-size:12px;'
            'color:#3949ab;text-align:right;border-bottom:2px solid #c5cae9;">Cost</th>'
            '<th style="padding:8px 14px;font-family:Arial,sans-serif;font-size:12px;'
            'color:#3949ab;text-align:left;border-bottom:2px solid #c5cae9;">Order ID</th>'
            '</tr>'
            + rows +
            f'<tr bgcolor="#e3f2fd">'
            f'<td colspan="3" style="padding:10px 14px;font-family:Arial,sans-serif;font-size:13px;'
            f'font-weight:bold;color:#1565c0;">Total Deployed</td>'
            f'<td style="padding:10px 14px;font-family:Arial,sans-serif;font-size:15px;'
            f'font-weight:bold;color:#1565c0;text-align:right;">${total_cost:,.2f}</td>'
            f'<td></td></tr>'
            '</table>'
            '<p style="font-family:Arial,sans-serif;font-size:13px;color:#546e7a;margin:20px 0 0;">'
            'Your positions are now live. Monitor them in your brokerage account. '
            'Stop losses are active per your approved trade parameters.</p>'
            '</td></tr>'
            # Footer
            '<tr><td bgcolor="#0d1b2a" style="padding:14px 32px;text-align:center;border-radius:0 0 8px 8px;">'
            '<p style="font-family:Arial,sans-serif;font-size:11px;color:#546e7a;margin:0;">'
            f'AI Trading Scanner &middot; Automated Market Analysis &middot; {now.strftime("%B %d, %Y")}</p>'
            '</td></tr>'
            '</table></td></tr></table></body></html>\n'
        )

    def validate(self) -> bool:
        """Validate write access to notification output directory."""
        try:
            test_file = self.out_dir / "test_notification_write.txt"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            return True
        except Exception as exc:
            self.log_error(f"Notification validation failed: {exc}")
            return False
