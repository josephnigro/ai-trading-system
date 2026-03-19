"""
Scoring engine - combines signals, risk management, and filtering.
Produces TradeProposal objects ready for user approval.
"""

from typing import List, Optional
from ..core.base_module import BaseModule
from ..core.signal import Signal
from ..core.trade_proposal import TradeProposal, TradeProposalStatus
from ..risk_management import RiskManager


class ScoringEngine(BaseModule):
    """
    Scoring and proposal engine.
    Converts signals -> proposals with position sizing and risk assessment.
    """
    
    def __init__(self, risk_manager: RiskManager):
        super().__init__("ScoringEngine")
        self.risk_manager = risk_manager
        self.proposals: List[TradeProposal] = []
        self.last_rejection_reason: str = ""
    
    def create_proposal(self, signal: Signal) -> Optional[TradeProposal]:
        """
        Create a trade proposal from a signal.
        
        Args:
            signal: Trading signal
        
        Returns:
            TradeProposal or None if signal doesn't pass checks
        """
        try:
            self.last_rejection_reason = ""

            # Validate signal quality
            if signal.overall_confidence < 50:
                self.log_error(f"{signal.ticker}: Low confidence ({signal.overall_confidence:.0f}%)")
                self.last_rejection_reason = "low_confidence"
                return None
            
            if signal.reward_to_risk < 1.0:
                self.log_error(f"{signal.ticker}: Poor risk/reward ratio ({signal.reward_to_risk:.2f})")
                self.last_rejection_reason = "risk_reward_fail"
                return None
            
            # Check if we can open position
            if not self.risk_manager.can_open_position():
                self.log_error(f"{signal.ticker}: Position limit reached")
                self.last_rejection_reason = "position_limit_reached"
                return None
            
            # Calculate position size
            shares = self.risk_manager.calculate_position_size(signal)
            if shares <= 0:
                self.log_error(f"{signal.ticker}: Invalid position size")
                self.last_rejection_reason = "invalid_position_size"
                return None
            
            # Check risk limits
            if not self.risk_manager.can_risk_trade(signal):
                self.log_error(f"{signal.ticker}: Exceeds risk limits")
                self.last_rejection_reason = "risk_filter_failed"
                return None
            
            # Calculate targets
            profit_target, stop_loss = self.risk_manager.calculate_targets(signal)
            
            # Calculate risk amount
            risk_amount = shares * abs(signal.entry_price - stop_loss)
            position_value = shares * signal.entry_price
            position_pct = (position_value / self.risk_manager.config.account_size) * 100
            
            # Create proposal
            proposal = TradeProposal(
                signal=signal,
                shares=shares,
                position_size_pct=position_pct,
                risk_amount=risk_amount,
                status=TradeProposalStatus.PENDING
            )
            
            # Update signal with calculated targets
            signal.profit_target = profit_target
            signal.stop_loss = stop_loss
            
            self.proposals.append(proposal)
            return proposal
        
        except Exception as e:
            self.log_error(f"Failed to create proposal for {signal.ticker}: {str(e)}")
            self.last_rejection_reason = "scoring_exception"
            return None
    
    def get_pending_proposals(self) -> List[TradeProposal]:
        """Get all pending proposals."""
        return [p for p in self.proposals if p.is_pending]
    
    def approve_proposal(self, trade_id: str, notes: str = "") -> bool:
        """Approve a proposal."""
        for proposal in self.proposals:
            if proposal.trade_id == trade_id:
                proposal.approve(notes)
                return True
        return False
    
    def reject_proposal(self, trade_id: str, reason: str = "") -> bool:
        """Reject a proposal."""
        for proposal in self.proposals:
            if proposal.trade_id == trade_id:
                proposal.reject(reason)
                return True
        return False
    
    def validate(self) -> bool:
        """Validate scoring engine is working."""
        return self.risk_manager.validate()
