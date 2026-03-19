"""
TradeProposal class - represents a proposed trade ready for user approval.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from .signal import Signal, SignalType


class TradeProposalStatus(Enum):
    """Status of a trade proposal."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


@dataclass
class TradeProposal:
    """
    Represents a trade proposal ready for user approval.
    
    Contains signal + position sizing + risk analysis.
    User sees this and decides: yes/no.
    """
    
    # Identity
    trade_id: str = ""
    signal: Optional[Signal] = None
    
    # Position sizing
    shares: int = 0
    position_size_pct: float = 0.0  # % of account
    risk_amount: float = 0.0  # $ amount at risk
    
    # Status
    status: TradeProposalStatus = TradeProposalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    
    # User notes
    approval_notes: str = ""
    rejection_reason: str = ""
    
    # Execution details
    execution_price: Optional[float] = None
    actual_shares: Optional[int] = None
    order_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate trade ID if not provided."""
        if not self.trade_id and self.signal:
            self.trade_id = f"PROPOSAL_{self.signal.signal_id}"
    
    @property
    def is_pending(self) -> bool:
        """Check if proposal is pending approval."""
        return self.status == TradeProposalStatus.PENDING
    
    @property
    def is_approved(self) -> bool:
        """Check if proposal is approved."""
        return self.status == TradeProposalStatus.APPROVED
    
    @property
    def is_executed(self) -> bool:
        """Check if proposal has been executed."""
        return self.status == TradeProposalStatus.EXECUTED
    
    def approve(self, notes: str = "") -> None:
        """Mark proposal as approved."""
        self.status = TradeProposalStatus.APPROVED
        self.approved_at = datetime.utcnow()
        self.approval_notes = notes
    
    def reject(self, reason: str = "") -> None:
        """Mark proposal as rejected."""
        self.status = TradeProposalStatus.REJECTED
        self.rejection_reason = reason
    
    def mark_executed(self, order_id: str, execution_price: float, actual_shares: int) -> None:
        """Mark proposal as executed."""
        self.status = TradeProposalStatus.EXECUTED
        self.executed_at = datetime.utcnow()
        self.order_id = order_id
        self.execution_price = execution_price
        self.actual_shares = actual_shares
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'trade_id': self.trade_id,
            'signal': self.signal.to_dict() if self.signal else None,
            'shares': self.shares,
            'position_size_pct': self.position_size_pct,
            'risk_amount': self.risk_amount,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'approval_notes': self.approval_notes,
            'rejection_reason': self.rejection_reason,
            'execution_price': self.execution_price,
            'actual_shares': self.actual_shares,
            'order_id': self.order_id,
        }
    
    def summary(self) -> str:
        """Return a clean summary for display."""
        if self.signal is None:
            return (
                f"{self.trade_id}\n"
                f"  Shares: {self.shares} ({self.position_size_pct:.1f}% of account)\n"
                f"  Risk: ${self.risk_amount:.2f}\n"
                f"  Status: {self.status.value}"
            )

        return (
            f"{self.trade_id}\n"
            f"  Signal: {self.signal.signal_type.value} {self.signal.ticker} @ ${self.signal.entry_price:.2f}\n"
            f"  Shares: {self.shares} ({self.position_size_pct:.1f}% of account)\n"
            f"  Risk: ${self.risk_amount:.2f}\n"
            f"  Target: ${self.signal.profit_target:.2f} | Stop: ${self.signal.stop_loss:.2f}\n"
            f"  Confidence: {self.signal.overall_confidence:.0f}% | R:R: {self.signal.reward_to_risk:.2f}\n"
            f"  Status: {self.status.value}"
        )
