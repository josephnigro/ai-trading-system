"""Risk manager for position sizing and portfolio management."""

import pandas as pd
from typing import Dict, List, Optional


class RiskManager:
    """Manages position sizing and portfolio risk constraints."""
    
    def __init__(self, account_size: float = 300, max_positions: int = 3):
        self.account_size = account_size
        self.max_positions = max_positions
        self.position_size = account_size / max_positions
        self.profit_target_pct = 0.15  # 15% profit target
    
    def calculate_position_size(self, stock_price: float) -> int:
        """Calculate shares to buy based on position size."""
        return int(self.position_size / stock_price)
    
    def calculate_sell_target(self, buy_price: float) -> float:
        """Calculate profit target price."""
        return buy_price * (1 + self.profit_target_pct)
    
    def check_constraints(self, signal_count: int) -> bool:
        """Check if trading constraints are met."""
        return signal_count < self.max_positions
