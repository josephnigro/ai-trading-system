"""
Risk management module - position sizing, limits, and risk controls.
Refactored from existing risk_manager.py
"""

from dataclasses import dataclass
from typing import Optional
from ..core.base_module import BaseModule
from ..core.signal import Signal, SignalType


@dataclass
class RiskConfig:
    """Risk management configuration."""
    account_size: float = 100000.0
    risk_per_trade_pct: float = 1.0  # Risk 1% per trade
    max_position_pct: float = 5.0  # Max 5% per position
    max_daily_risk_pct: float = 2.0  # Max 2% per day
    max_concurrent_positions: int = 3
    profit_target_pct: float = 15.0  # Target +15%
    stop_loss_pct: float = 5.0  # Stop at -5%
    max_hold_days: int = 7


class RiskManager(BaseModule):
    """
    Risk management module.
    Calculates position sizes, enforces limits, manages exposure.
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        super().__init__("RiskManager")
        self.config = config or RiskConfig()
        self.current_exposure = 0.0
        self.daily_risk_used = 0.0
        self.open_positions = 0
    
    def calculate_position_size(self, signal: Signal) -> int:
        """
        Calculate how many shares to buy based on position sizing rules.
        
        Args:
            signal: Trading signal with entry price and stop loss
        
        Returns:
            Number of shares to trade
        """
        try:
            # Risk amount
            risk_amount = self.config.account_size * (self.config.risk_per_trade_pct / 100.0)
            
            # Difference between entry and stop
            if signal.signal_type == SignalType.BUY:
                price_diff = signal.entry_price - signal.stop_loss
            else:  # SHORT
                price_diff = signal.stop_loss - signal.entry_price
            
            if price_diff <= 0:
                self.log_error(f"Invalid stop loss for {signal.ticker}")
                return 0
            
            # Calculate shares
            shares = int(risk_amount / price_diff)
            
            # Check position size limit
            position_value = shares * signal.entry_price
            max_position_value = self.config.account_size * (self.config.max_position_pct / 100.0)
            
            if position_value > max_position_value:
                shares = int(max_position_value / signal.entry_price)
            
            return max(1, shares)
        
        except Exception as e:
            self.log_error(f"Position sizing error: {str(e)}")
            return 1
    
    def can_open_position(self) -> bool:
        """Check if we can open a new position."""
        return self.open_positions < self.config.max_concurrent_positions
    
    def can_risk_trade(self, signal: Signal) -> bool:
        """Check if we can risk this trade's capital."""
        shares = self.calculate_position_size(signal)
        risk_amount = shares * abs(signal.entry_price - signal.stop_loss)
        
        # Check if daily risk would exceed limit
        remaining_daily_risk = (
            self.config.account_size * 
            (self.config.max_daily_risk_pct / 100.0)
        )
        
        if (self.daily_risk_used + risk_amount) > remaining_daily_risk:
            self.log_error(
                f"Daily risk limit would be exceeded. "
                f"Used: ${self.daily_risk_used:.2f}, "
                f"Trade: ${risk_amount:.2f}, "
                f"Limit: ${remaining_daily_risk:.2f}"
            )
            return False
        
        return True
    
    def calculate_targets(self, signal: Signal) -> tuple:
        """
        Calculate profit target and stop loss based on signal.
        
        Returns:
            (profit_target, stop_loss)
        """
        entry = signal.entry_price
        
        if signal.signal_type == SignalType.BUY:
            target = entry * (1 + self.config.profit_target_pct / 100.0)
            stop = entry * (1 - self.config.stop_loss_pct / 100.0)
        else:  # SHORT
            target = entry * (1 - self.config.profit_target_pct / 100.0)
            stop = entry * (1 + self.config.stop_loss_pct / 100.0)
        
        return target, stop
    
    def mark_position_opened(self, shares: int, entry_price: float, risk_amount: float) -> None:
        """Track that a position was opened."""
        self.open_positions += 1
        self.current_exposure += shares * entry_price
        self.daily_risk_used += risk_amount
    
    def mark_position_closed(self, shares: int, entry_price: float, risk_amount: float) -> None:
        """Track that a position was closed."""
        self.open_positions = max(0, self.open_positions - 1)
        self.current_exposure -= shares * entry_price
    
    def reset_daily_limits(self) -> None:
        """Reset daily risk tracking (call each day)."""
        self.daily_risk_used = 0.0
    
    def validate(self) -> bool:
        """Validate configuration is sound."""
        if self.config.account_size <= 0:
            self.log_error("Account size must be > 0")
            return False
        
        if self.config.risk_per_trade_pct <= 0 or self.config.risk_per_trade_pct > 10:
            self.log_error("Risk per trade should be 0-10%")
            return False
        
        return True
    
    def health_check(self):
        """Return risk manager status."""
        base = super().health_check()
        base.update({
            'account_size': self.config.account_size,
            'risk_per_trade': f"{self.config.risk_per_trade_pct}%",
            'open_positions': self.open_positions,
            'current_exposure': f"${self.current_exposure:,.2f}",
            'daily_risk_used': f"${self.daily_risk_used:,.2f}",
        })
        return base
