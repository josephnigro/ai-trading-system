# ==============================
# CONFIGURATION & KILL SWITCH MODULE
# ==============================
# System configuration and emergency halt controls

import json
import os
from datetime import datetime

class SystemConfig:
    """
    Manages system configuration and trading parameters
    """
    
    def __init__(self, config_file='system_config.json'):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or use defaults"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            return self._default_config()
    
    def _default_config(self):
        """Default system configuration"""
        return {
            'account_settings': {
                'account_size': 300,        # Small account ($300)
                'risk_per_trade': 0.05,     # 5% per trade (allows smaller positions)
                'max_position_size': 0.33,  # 33% position size (can hold 3 concurrent trades)
                'max_concurrent_trades': 3,
                'max_daily_loss': 0.10,    # 10% max loss per day
            },
            'trading_settings': {
                'min_price': 0.50,          # Allow penny stocks
                'max_price': 100.00,        # ✅ RESTRICT to < $100 for tradability
                'min_volume_dollars': 50000,  # Lower volume requirement
                'reward_to_risk': 1.5,      # Less strict reward/risk
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
                'phone_number': '',
                'paper_account': True,
            },
            'market_conditions': {
                'trading_enabled': True,
                'circuit_breaker_enabled': True,
                'vix_threshold': 50,  # Disable trading if VIX > 50
            }
        }
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"✓ Configuration saved to {self.config_file}")
    
    def get(self, key_path, default=None):
        """Get config value using dot notation"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        
        return value if value is not None else default
    
    def set(self, key_path, value):
        """Set config value using dot notation"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self.save_config()
    
    def print_config(self):
        """Print current configuration"""
        print("\n" + "="*60)
        print("SYSTEM CONFIGURATION")
        print("="*60)
        print(json.dumps(self.config, indent=2))
        print("="*60)


class KillSwitch:
    """
    Emergency kill switch - immediately halt all trading
    """
    
    def __init__(self, config):
        self.config = config
        self.is_active = False
        self.kill_switch_timestamp = None
        self.kill_reason = None
    
    def activate(self, reason='Manual activation'):
        """
        Activate kill switch - halt all trading immediately
        """
        self.is_active = True
        self.kill_switch_timestamp = datetime.now().isoformat()
        self.kill_reason = reason
        
        # Also disable live trading in config
        self.config.set('automation.live_trading_enabled', False)
        
        print("\n" + "🛑"*30)
        print("KILL SWITCH ACTIVATED")
        print("🛑"*30)
        print(f"Reason: {reason}")
        print(f"Time: {self.kill_switch_timestamp}")
        print("\n⚠️  ALL TRADING HALTED")
        print("🛑"*30 + "\n")
    
    def deactivate(self):
        """
        Deactivate kill switch - resume trading
        """
        self.is_active = False
        print("\n✓ Kill switch deactivated - trading resumed\n")
    
    def check_status(self):
        """Check if kill switch is active"""
        return self.is_active
    
    def get_status(self):
        """Get detailed kill switch status"""
        return {
            'is_active': self.is_active,
            'timestamp': self.kill_switch_timestamp,
            'reason': self.kill_reason
        }


class CircuitBreaker:
    """
    Automatic circuit breaker - halt trading if losses exceed threshold
    """
    
    def __init__(self, max_daily_loss_percent=2.0):
        self.max_daily_loss_percent = max_daily_loss_percent
        self.daily_pnl = 0.0
        self.account_size = 0.0
        self.is_broken = False
        self.break_timestamp = None
    
    def update_pnl(self, trade_pnl):
        """Update daily P&L"""
        self.daily_pnl += trade_pnl
    
    def check_breach(self, account_size):
        """Check if losses exceed threshold"""
        self.account_size = account_size
        max_loss = account_size * (self.max_daily_loss_percent / 100)
        
        if self.daily_pnl < -max_loss:
            self.is_broken = True
            self.break_timestamp = datetime.now().isoformat()
            return True
        
        return False
    
    def reset_daily(self):
        """Reset daily counters (call at market open)"""
        self.daily_pnl = 0.0
        self.is_broken = False
        self.break_timestamp = None
    
    def get_status(self):
        """Get circuit breaker status"""
        loss_limit = self.account_size * (self.max_daily_loss_percent / 100)
        
        return {
            'daily_pnl': self.daily_pnl,
            'loss_limit': -loss_limit,
            'remaining_risk': -loss_limit - self.daily_pnl,
            'is_broken': self.is_broken,
            'break_timestamp': self.break_timestamp
        }


class TradingHours:
    """
    Check if trading is within market hours
    """
    
    def __init__(self, start_time='09:30', end_time='16:00', timezone='America/New_York'):
        self.start_time = start_time
        self.end_time = end_time
        self.timezone = timezone
    
    def is_market_open(self):
        """Check if it's market hours"""
        from datetime import datetime
        
        # Get current time
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        current_day = now.weekday()  # 0=Monday, 4=Friday
        
        # Market closed on weekends
        if current_day >= 5:
            return False
        
        # Check if within trading hours
        if current_time >= self.start_time and current_time <= self.end_time:
            return True
        
        return False
    
    def get_time_to_market_open(self):
        """Get minutes until market open"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        market_open = datetime.strptime(self.start_time, '%H:%M').time()
        market_close = datetime.strptime(self.end_time, '%H:%M').time()
        
        current = now.time()
        
        if current < market_open:
            # Before market open today
            next_open = datetime.combine(now.date(), market_open)
            time_to_open = (next_open - now).total_seconds() / 60
        else:
            # After market close, market open tomorrow
            tomorrow = now.date() + timedelta(days=1)
            next_open = datetime.combine(tomorrow, market_open)
            time_to_open = (next_open - now).total_seconds() / 60
        
        return int(time_to_open)
