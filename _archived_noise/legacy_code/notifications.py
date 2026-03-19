# ==============================
# NOTIFICATIONS MODULE
# ==============================
# Send SMS alerts and notifications

import os
from datetime import datetime
from typing import Optional

class NotificationManager:
    """
    Manages notifications (SMS, Email, Console)
    Texts user with trading decisions for approval
    """
    
    def __init__(self, twilio_enabled: bool = False, phone_number: Optional[str] = None):
        """
        twilio_enabled: Set to True to send actual SMS (requires Twilio setup)
        phone_number: Your phone number to receive SMS
        """
        self.twilio_enabled = twilio_enabled
        self.phone_number = phone_number
        self.twilio_number: Optional[str] = None
        self.notification_log = []
        
        if twilio_enabled:
            try:
                from twilio.rest import Client  # type: ignore
                self.twilio_client = Client(
                    os.getenv('TWILIO_ACCOUNT_SID'),
                    os.getenv('TWILIO_AUTH_TOKEN')
                )
                self.twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
            except ImportError:
                print("⚠️  Twilio not installed. Install with: pip install twilio")
                self.twilio_enabled = False
    
    def send_signal_alert(self, ticker, signal_data, risk_data):
        """
        Send alert about a new trading signal
        Asks for approval before execution
        """
        signal = signal_data['signal']
        price = signal_data['price']
        rsi = signal_data['technical']['rsi']
        
        message = f"""
🚨 NEW {signal} SIGNAL: {ticker}

Price: ${price:.2f}
RSI: {rsi:.1f}
Entry: ${risk_data.get('entry', price):.2f}
Stop: ${risk_data.get('stop_loss'):.2f}
Target: ${risk_data.get('target'):.2f}
Risk: ${risk_data.get('risk_dollars', 0):.2f}
Shares: {risk_data.get('shares', 0)}

⏳ AWAITING YOUR APPROVAL TO TRADE
Reply: YES to approve, NO to skip
"""
        
        self._send_notification("SIGNAL_ALERT", message)
        return message
    
    def send_trade_confirmation(self, trade_data):
        """
        Send confirmation of executed trade
        """
        message = f"""
✅ TRADE EXECUTED: {trade_data['ticker']}

Entry: ${trade_data['entry_price']:.2f}
Shares: {trade_data['shares']}
Position Value: ${trade_data['position_value']:.2f}
Risk: ${trade_data['risk_dollars']:.2f}
Stop Loss: ${trade_data['stop_loss']:.2f}
Target: ${trade_data['target']:.2f}

Trade ID: {trade_data.get('trade_id', 'N/A')}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        self._send_notification("TRADE_EXECUTED", message)
        return message
    
    def send_trade_closed(self, trade_data):
        """
        Send notification when trade is closed
        """
        pnl = trade_data.get('pnl_dollars', 0)
        pnl_pct = trade_data.get('pnl_percent', 0)
        
        emoji = "✅" if pnl > 0 else "❌" if pnl < 0 else "⚪"
        
        message = f"""
{emoji} TRADE CLOSED: {trade_data['ticker']}

Exit Price: ${trade_data['exit_price']:.2f}
P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)
Reason: {trade_data.get('exit_reason', 'N/A')}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        self._send_notification("TRADE_CLOSED", message)
        return message
    
    def send_system_alert(self, alert_type, message):
        """
        Send system alerts (kill switch, errors, etc)
        """
        full_message = f"""
🚨 SYSTEM ALERT: {alert_type}

{message}

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        self._send_notification("SYSTEM_ALERT", full_message)
        return full_message
    
    def send_daily_summary(self, summary_data):
        """
        Send daily trading summary
        """
        message = f"""
📊 DAILY TRADING SUMMARY

Date: {datetime.now().strftime('%Y-%m-%d')}
Signals Generated: {summary_data.get('signals_count', 0)}
Trades Executed: {summary_data.get('trades_count', 0)}
Daily P&L: ${summary_data.get('daily_pnl', 0):.2f}
Open Positions: {summary_data.get('open_positions', 0)}
Win Rate: {summary_data.get('win_rate', 0):.1f}%
"""
        
        self._send_notification("DAILY_SUMMARY", message)
        return message
    
    def _send_notification(self, notification_type, message):
        """
        Internal method to send notification via all channels
        """
        # Log the notification
        self.notification_log.append({
            'timestamp': datetime.now().isoformat(),
            'type': notification_type,
            'message': message
        })
        
        # Always print to console
        print(f"\n{'='*60}")
        print(f"📢 NOTIFICATION - {notification_type}")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        
        # Send SMS if enabled
        if self.twilio_enabled and self.phone_number:
            self._send_sms(message, notification_type)
    
    def _send_sms(self, message, notification_type):
        """
        Send SMS via Twilio
        Requires Twilio credentials in environment variables
        """
        if not self.twilio_enabled:
            return

        if not self.phone_number:
            return
        
        try:
            # Truncate message for SMS (160 char limit)
            sms_message = message[:160]
            recipient = str(self.phone_number)
            
            self.twilio_client.messages.create(
                body=sms_message,
                from_=self.twilio_number,
                to=recipient
            )
            
            print(f"✓ SMS sent to {self.phone_number}")
        except Exception as e:
            print(f"✗ Failed to send SMS: {e}")
    
    def setup_twilio(self, account_sid, auth_token, twilio_number, phone_number):
        """
        Setup Twilio credentials for SMS
        """
        os.environ['TWILIO_ACCOUNT_SID'] = account_sid
        os.environ['TWILIO_AUTH_TOKEN'] = auth_token
        os.environ['TWILIO_PHONE_NUMBER'] = twilio_number
        
        self.phone_number = phone_number
        self.twilio_enabled = True
        
        print("✓ Twilio configured for SMS notifications")


class ManualApprovalHandler:
    """
    Handles manual approval workflow
    User gets a prompt to approve/reject each trade signal
    """
    
    def __init__(self, require_approval=True):
        self.require_approval = require_approval
        self.approval_log = []
    
    def request_approval(self, ticker, signal_data, risk_data):
        """
        Request user approval for a trade
        Returns True if approved, False if rejected
        """
        
        if not self.require_approval:
            return True
        
        print(f"\n{'='*60}")
        print(f"⚠️  TRADE APPROVAL REQUIRED")
        print(f"{'='*60}")
        print(f"\nTicker: {ticker}")
        print(f"Signal: {signal_data['signal']}")
        print(f"Price: ${signal_data['price']:.2f}")
        print(f"Entry: ${risk_data.get('entry', signal_data['price']):.2f}")
        print(f"Stop Loss: ${risk_data.get('stop_loss'):.2f}")
        print(f"Target: ${risk_data.get('target'):.2f}")
        print(f"Risk: ${risk_data.get('risk_dollars', 0):.2f}")
        print(f"Shares: {risk_data.get('shares', 0)}")
        print(f"\nReason: {risk_data.get('reason', 'Market opportunity')}")
        print(f"{'='*60}")
        
        while True:
            response = input("\nAPPROVE TRADE? (yes/no/skip): ").strip().lower()
            
            if response in ['yes', 'y']:
                self.approval_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'ticker': ticker,
                    'decision': 'APPROVED'
                })
                return True
            elif response in ['no', 'n']:
                self.approval_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'ticker': ticker,
                    'decision': 'REJECTED'
                })
                return False
            elif response in ['skip', 's']:
                self.approval_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'ticker': ticker,
                    'decision': 'SKIPPED'
                })
                return False
            else:
                print("Please enter 'yes', 'no', or 'skip'")
