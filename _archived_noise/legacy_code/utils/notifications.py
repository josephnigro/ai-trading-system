"""Notifications and user approval handling."""

import os
from datetime import datetime
from typing import Optional


class NotificationManager:
    """Manages notifications (SMS, Email, Console)."""
    
    def __init__(self, twilio_enabled: bool = False, phone_number: Optional[str] = None):
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
                print("⚠️  Twilio not installed")
                self.twilio_enabled = False
    
    def send_signal_alert(self, ticker, signal_data, risk_data):
        """Send alert about new trading signal."""
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

⏳ AWAITING YOUR APPROVAL
"""
        
        self._send_notification("SIGNAL_ALERT", message)
        return message
    
    def send_trade_confirmation(self, trade_data):
        """Send trade execution confirmation."""
        message = f"""
✅ TRADE EXECUTED: {trade_data['ticker']}

Entry: ${trade_data['entry_price']:.2f}
Shares: {trade_data['shares']}
Position: ${trade_data['position_value']:.2f}
Risk: ${trade_data['risk_dollars']:.2f}
Stop: ${trade_data['stop_loss']:.2f}
Target: ${trade_data['target']:.2f}
"""
        
        self._send_notification("TRADE_EXECUTED", message)
        return message
    
    def send_trade_closed(self, trade_data):
        """Send notification when trade is closed."""
        pnl = trade_data.get('pnl_dollars', 0)
        pnl_pct = trade_data.get('pnl_percent', 0)
        emoji = "✅" if pnl > 0 else "❌" if pnl < 0 else "⚪"
        
        message = f"""
{emoji} TRADE CLOSED: {trade_data['ticker']}

Exit: ${trade_data['exit_price']:.2f}
P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)
"""
        
        self._send_notification("TRADE_CLOSED", message)
        return message
    
    def send_system_alert(self, alert_type, message):
        """Send system alerts."""
        full_message = f"🚨 {alert_type}\n\n{message}"
        self._send_notification("SYSTEM_ALERT", full_message)
        return full_message
    
    def _send_notification(self, notification_type, message):
        """Send notification via all channels."""
        self.notification_log.append({
            'timestamp': datetime.now().isoformat(),
            'type': notification_type,
            'message': message
        })
        
        print(f"\n{'='*60}")
        print(f"📢 {notification_type}")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        
        if self.twilio_enabled and self.phone_number:
            self._send_sms(message[:160])
    
    def _send_sms(self, message):
        """Send SMS via Twilio."""
        if not self.twilio_enabled:
            return

        if not self.phone_number:
            return
        
        try:
            recipient = str(self.phone_number)
            self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_number,
                to=recipient
            )
            print(f"✓ SMS sent")
        except Exception as e:
            print(f"✗ SMS failed: {e}")


class ManualApprovalHandler:
    """Handles manual trade approval workflow."""
    
    def __init__(self, require_approval=True):
        self.require_approval = require_approval
        self.approval_log = []
    
    def request_approval(self, signal_data):
        """Request manual approval for a trade signal."""
        if not self.require_approval:
            return True
        
        ticker = signal_data['ticker']
        signal_type = signal_data['signal']
        price = signal_data['price']
        
        print(f"\n{'='*60}")
        print(f"🔔 TRADE APPROVAL REQUIRED")
        print(f"{'='*60}")
        print(f"Ticker: {ticker}")
        print(f"Signal: {signal_type}")
        print(f"Price: ${price:.2f}")
        print(f"{'='*60}")
        
        while True:
            response = input("Approve this trade? (yes/no): ").lower().strip()
            
            if response in ['yes', 'y']:
                self.approval_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'ticker': ticker,
                    'signal': signal_type,
                    'approved': True
                })
                return True
            elif response in ['no', 'n']:
                self.approval_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'ticker': ticker,
                    'signal': signal_type,
                    'approved': False
                })
                return False
            else:
                print("Please enter yes or no")
