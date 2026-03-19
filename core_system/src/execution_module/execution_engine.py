"""
Execution module - handles trade execution via broker API.
"""

from typing import Dict, Optional
from enum import Enum
from ..core.base_module import BaseModule
from ..core.execution_record import ExecutionRecord


class ExecutionStatus(Enum):
    """Execution status."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class BrokerIntegration(BaseModule):
    """
    Broker API integration interface.
    Implemented for Alpaca, can be extended for other brokers.
    """
    
    def __init__(self, name: str = "BrokerIntegration"):
        super().__init__(name)
    
    def place_buy_order(self, symbol: str, shares: int, limit_price: Optional[float] = None) -> Dict:
        """Place a buy order."""
        raise NotImplementedError
    
    def place_sell_order(self, symbol: str, shares: int, limit_price: Optional[float] = None) -> Dict:
        """Place a sell order."""
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        raise NotImplementedError
    
    def get_balance(self) -> float:
        """Get account balance."""
        raise NotImplementedError


class ExecutionModule(BaseModule):
    """
    Execution module - manages trade execution.
    """
    
    def __init__(self, broker: BrokerIntegration):
        super().__init__("ExecutionModule")
        self.broker = broker
        self.executions: Dict[str, ExecutionRecord] = {}
    
    def execute_buy_order(
        self,
        trade_id: str,
        ticker: str,
        shares: int,
        limit_price: Optional[float] = None
    ) -> Optional[ExecutionRecord]:
        """
        Execute a buy order.
        
        Returns:
            ExecutionRecord if successful, None if failed
        """
        try:
            # Place order with broker
            result = self.broker.place_buy_order(ticker, shares, limit_price)
            
            if not result.get('success'):
                self.log_error(f"Buy order failed for {ticker}: {result.get('error')}")
                return None
            
            # Create execution record
            execution = ExecutionRecord(
                execution_id=f"EXEC_{trade_id}",
                order_id=str(result.get('order_id') or f"SIM_{trade_id}"),
                trade_id=trade_id,
                ticker=ticker,
                shares=shares
            )
            
            execution.mark_filled(
                execution_price=result.get('price', 0.0)
            )
            
            self.executions[trade_id] = execution
            return execution
        
        except Exception as e:
            self.log_error(f"Execution error: {str(e)}")
            return None
    
    def close_position(
        self,
        trade_id: str,
        exit_price: float,
        reason: str = "manual"
    ) -> bool:
        """Close an open position."""
        if trade_id not in self.executions:
            return False
        
        execution = self.executions[trade_id]
        execution.close_position(exit_price, reason)
        return True
    
    def validate(self) -> bool:
        """Validate broker connection is working."""
        if self.broker is None:
            return True
        try:
            return self.broker.validate()
        except Exception as e:
            self.log_error(f"Broker validation failed: {str(e)}")
            return False
