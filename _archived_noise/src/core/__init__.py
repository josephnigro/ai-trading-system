"""
Core data structures and classes for the trading system.
"""

from .signal import Signal, SignalType
from .trade_proposal import TradeProposal
from .execution_record import ExecutionRecord

__all__ = ['Signal', 'SignalType', 'TradeProposal', 'ExecutionRecord']
