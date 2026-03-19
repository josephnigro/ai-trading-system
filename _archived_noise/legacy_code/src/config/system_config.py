"""
# ============================================================================
# SYSTEM CONFIGURATION MODULE
# ============================================================================
# Centralized configuration for the entire trading system
# ============================================================================
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional


# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

DEFAULT_CONFIG = {
    # Account settings
    'account_size': 300,
    'max_positions': 3,
    'profit_target_pct': 0.15,
    'stop_loss_pct': 0.05,
    'max_hold_days': 7,
    
    # Data source
    'data_provider': 'alpha_vantage',
    'api_timeout': 10,
    
    # Trading
    'paper_trading': True,  # Using PAPER Alpaca account for testing
    'auto_trade': True,  # ENABLED: Machine will execute trades automatically
    'kill_switch_enabled': True,
    'kill_switch_triggered': False,
    
    # Scanner
    'scan_period': '1y',
    'min_price': 0.5,
}


# ============================================================================
# SYSTEM CONFIG CLASS
# ============================================================================

class SystemConfig:
    """
    Centralized configuration management.
    
    Features:
    - Loads from environment variables
    - Maintains default values
    - Type safety
    """
    
    def __init__(self):
        """Initialize configuration from env vars and defaults."""
        self.config = DEFAULT_CONFIG.copy()
        self._load_from_env()
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Data source
        self.config['alpha_vantage_key'] = os.getenv(
            'ALPHA_VANTAGE_API_KEY',
            ''
        )
        
        # Alpaca
        self.config['alpaca_api_key'] = os.getenv(
            'ALPACA_API_KEY',
            ''
        )
        self.config['alpaca_api_secret'] = os.getenv(
            'ALPACA_API_SECRET',
            ''
        )

        # Safety controls
        self.config['max_hold_days'] = int(os.getenv('MAX_HOLD_DAYS', str(self.config['max_hold_days'])))
        self.config['kill_switch_enabled'] = os.getenv('KILL_SWITCH_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')
        self.config['kill_switch_triggered'] = os.getenv('KILL_SWITCH', 'false').lower() in ('1', 'true', 'yes', 'on')
        
        # Logging
        self.config['log_dir'] = os.getenv('LOG_DIR', 'logs')
        self.config['trade_log_dir'] = os.getenv('TRADE_LOG_DIR', 'trade_logs')
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
    
    def print_summary(self) -> None:
        """Print configuration summary."""
        print("\n" + "="*60)
        print("SYSTEM CONFIGURATION")
        print("="*60)
        
        print("\nAccount:")
        print(f"  Size: ${self.config.get('account_size')}")
        print(f"  Max Positions: {self.config.get('max_positions')}")
        profit_pct = self.config.get('profit_target_pct') or 0
        print(f"  Profit Target: {profit_pct*100:.0f}%")
        
        print("\nTrading:")
        print(f"  Mode: {'PAPER' if self.config.get('paper_trading') else 'LIVE'}")
        print(f"  Auto Trade: {'ON' if self.config.get('auto_trade') else 'OFF'}")
        
        print("\nData:")
        print(f"  Provider: {self.config.get('data_provider')}")
        print(f"  API Key: {'SET' if self.config.get('alpha_vantage_key') else 'NOT SET'}")
        
        print("="*60 + "\n")
