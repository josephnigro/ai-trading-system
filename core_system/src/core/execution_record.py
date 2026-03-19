"""
ExecutionRecord class - represents a completed trade execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from .signal import SignalType


class ExecutionStatus(Enum):
    """Status of an execution."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class ExecutionRecord:
    """
    Complete record of a trade execution.
    
    Audit trail for compliance and P&L tracking.
    """
    
    # Execution identity
    execution_id: str = ""
    order_id: str = ""
    trade_id: str = ""
    
    # Trade details
    ticker: str = ""
    signal_type: SignalType = SignalType.BUY
    shares: int = 0
    
    # Pricing
    entry_price: float = 0.0
    execution_price: float = 0.0
    profit_target: float = 0.0
    stop_loss: float = 0.0
    
    # Status
    status: ExecutionStatus = ExecutionStatus.PENDING
    executed_at: Optional[datetime] = None
    
    # P&L tracking
    exit_price: Optional[float] = None
    exit_reason: str = ""  # profit_target, stop_loss, time_stop, manual
    closed_at: Optional[datetime] = None
    realized_p_and_l: float = 0.0
    realized_p_and_l_pct: float = 0.0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    commission: float = 0.0
    notes: str = ""
    
    def mark_filled(self, execution_price: float, execution_time: Optional[datetime] = None) -> None:
        """Mark execution as filled."""
        self.status = ExecutionStatus.FILLED
        self.execution_price = execution_price
        self.executed_at = execution_time or datetime.utcnow()
    
    def close_position(
        self, 
        exit_price: float, 
        reason: str = "manual",
        close_time: Optional[datetime] = None
    ) -> None:
        """Close the position and calculate P&L."""
        self.exit_price = exit_price
        self.exit_reason = reason
        self.closed_at = close_time or datetime.utcnow()
        
        # Calculate P&L
        if self.signal_type == SignalType.BUY:
            gross_pnl = (exit_price - self.execution_price) * self.shares
        elif self.signal_type == SignalType.SHORT:
            gross_pnl = (self.execution_price - exit_price) * self.shares
        else:
            gross_pnl = 0.0
        
        self.realized_p_and_l = gross_pnl - self.commission
        
        if self.execution_price > 0:
            self.realized_p_and_l_pct = (self.realized_p_and_l / (self.execution_price * self.shares)) * 100
    
    @property
    def is_open(self) -> bool:
        """Check if position is still open."""
        return self.exit_price is None
    
    @property
    def hold_duration(self) -> Optional[float]:
        """Get hold duration in hours."""
        if not self.executed_at:
            return None
        close_time = self.closed_at or datetime.utcnow()
        delta = close_time - self.executed_at
        return delta.total_seconds() / 3600
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'execution_id': self.execution_id,
            'order_id': self.order_id,
            'trade_id': self.trade_id,
            'ticker': self.ticker,
            'signal_type': self.signal_type.value,
            'shares': self.shares,
            'entry_price': self.entry_price,
            'execution_price': self.execution_price,
            'profit_target': self.profit_target,
            'stop_loss': self.stop_loss,
            'status': self.status.value,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'exit_price': self.exit_price,
            'exit_reason': self.exit_reason,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'realized_p_and_l': self.realized_p_and_l,
            'realized_p_and_l_pct': self.realized_p_and_l_pct,
            'hold_duration_hours': self.hold_duration,
            'commission': self.commission,
            'created_at': self.created_at.isoformat(),
            'notes': self.notes,
        }
    
    def summary(self) -> str:
        """Return summary string."""
        status_str = f"Open - {self.hold_duration:.1f}h" if self.is_open else f"Closed - {self.exit_reason}"
        pnl_str = f"P&L: ${self.realized_p_and_l:.2f} ({self.realized_p_and_l_pct:+.2f}%)"
        return (
            f"{self.execution_id}\n"
            f"  {self.ticker} {self.signal_type.value} x{self.shares} @ ${self.execution_price:.2f}\n"
            f"  {status_str}\n"
            f"  {pnl_str}"
        )
