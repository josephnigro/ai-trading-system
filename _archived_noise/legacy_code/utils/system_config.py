"""System configuration and safety controls."""

import json
import os
from datetime import datetime, timedelta


class SystemConfig:
    """Manages configuration and trading parameters."""
    
    def __init__(self, config_file='system_config.json'):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or use defaults."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self):
        """Return default configuration."""
        return {
            'account_settings': {
                'account_size': 25000,
                'risk_per_trade': 0.01,
                'max_position_size': 0.05,
                'max_concurrent_trades': 5,
                'max_daily_loss': 0.02,
            },
            'trading_settings': {
                'min_price': 5.0,
                'min_volume_dollars': 1000000,
                'reward_to_risk': 2.0,
                'trading_hours': {
                    'start': '09:30',
                    'end': '16:00',
                    'timezone': 'America/New_York'
                },
            },
            'automation': {
                'auto_approval_enabled': False,
                'manual_approval_required': True,
                'paper_trading_mode': True,
                'live_trading_enabled': False,
            },
            'notifications': {
                'sms_enabled': False,
                'email_enabled': False,
                'console_enabled': True,
            },
            'broker_settings': {
                'platform': 'robinhood',
                'api_key': '',
                'paper_account': True,
            },
        }
    
    def save_config(self):
        """Save configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"✓ Configuration saved")
    
    def get(self, key_path, default=None):
        """Get config value using dot notation."""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        
        return value if value is not None else default
    
    def set(self, key_path, value):
        """Set config value using dot notation."""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self.save_config()
    
    def print_summary(self) -> None:
        """Print configuration summary."""
        print("\n" + "="*60)
        print("SYSTEM CONFIGURATION")
        print("="*60)
        
        print("\nAccount:")
        account_size = self.get('account_settings.account_size', 25000)
        max_positions = self.get('account_settings.max_concurrent_trades', 5)
        print(f"  Size: ${account_size:,.0f}")
        print(f"  Max Positions: {max_positions}")
        
        print("\nTrading:")
        paper_mode = self.get('automation.paper_trading_mode', True)
        auto_trade = self.get('automation.auto_approval_enabled', False)
        print(f"  Mode: {'PAPER' if paper_mode else 'LIVE'}")
        print(f"  Auto Trade: {'ON' if auto_trade else 'OFF'}")
        
        print("\nData:")
        broker_platform = self.get('broker_settings.platform', 'robinhood')
        api_key_set = bool(self.get('broker_settings.api_key'))
        print(f"  Broker: {broker_platform}")
        print(f"  API Key: {'SET' if api_key_set else 'NOT SET'}")
        
        print("="*60 + "\n")


class KillSwitch:
    """Emergency kill switch to halt all trading."""
    
    def __init__(self, config):
        self.config = config
        self.is_active = False
        self.kill_timestamp = None
        self.kill_reason = None
    
    def activate(self, reason='Manual activation'):
        """Activate kill switch - halt all trading."""
        self.is_active = True
        self.kill_timestamp = datetime.now().isoformat()
        self.kill_reason = reason
        self.config.set('automation.live_trading_enabled', False)
        
        print("\n" + "🛑"*20)
        print("KILL SWITCH ACTIVATED")
        print(f"Reason: {reason}")
        print("🛑"*20 + "\n")
    
    def deactivate(self):
        """Deactivate kill switch."""
        self.is_active = False
        print("✓ Kill switch deactivated\n")
    
    def check_status(self):
        """Check if kill switch is active."""
        return self.is_active


class CircuitBreaker:
    """Automatic halt if daily losses exceed threshold."""
    
    def __init__(self, max_daily_loss_percent=2.0):
        self.max_daily_loss_percent = max_daily_loss_percent
        self.daily_pnl = 0.0
        self.account_size = 0.0
        self.is_broken = False
    
    def update_pnl(self, trade_pnl):
        """Update daily P&L."""
        self.daily_pnl += trade_pnl
    
    def check_breach(self, account_size):
        """Check if losses exceed threshold."""
        self.account_size = account_size
        max_loss = account_size * (self.max_daily_loss_percent / 100)
        
        if self.daily_pnl < -max_loss:
            self.is_broken = True
            return True
        return False
    
    def reset_daily(self):
        """Reset daily counters."""
        self.daily_pnl = 0.0
        self.is_broken = False


class TradingHours:
    """Check if trading is within market hours."""
    
    def __init__(self, start_time='09:30', end_time='16:00'):
        self.start_time = start_time
        self.end_time = end_time
    
    def is_market_open(self):
        """Check if it's market hours."""
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        day = now.weekday()
        
        if day >= 5:  # Weekend
            return False
        
        return self.start_time <= current_time <= self.end_time
    
    def minutes_to_open(self):
        """Minutes until market opens."""
        now = datetime.now()
        market_open = datetime.strptime(self.start_time, '%H:%M').time()
        
        current = now.time()
        if current < market_open:
            next_open = datetime.combine(now.date(), market_open)
            mins = (next_open - now).total_seconds() / 60
        else:
            tomorrow = now.date() + timedelta(days=1)
            next_open = datetime.combine(tomorrow, market_open)
            mins = (next_open - now).total_seconds() / 60
        
        return int(mins)
