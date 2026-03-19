"""
# ============================================================================
# PAPER TRADING ACCOUNT MODULE
# ============================================================================
# Simulates trading without real money for testing and validation
# ============================================================================
"""

from datetime import datetime
from typing import Dict, Optional, List


# ============================================================================
# PAPER TRADING ACCOUNT CLASS
# ============================================================================

class PaperTradingAccount:
    """
    Simulates trading account for backtesting and validation.
    
    Features:
    - Virtual cash balance
    - Simulated buy/sell execution
    - Position tracking
    - P&L calculation
    - Trade history logging
    """
    
    def __init__(self, starting_balance: float = 300.0):
        """
        Initialize paper trading account.
        
        Args:
            starting_balance: Starting cash amount (default $300)
        """
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.positions: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
    
    # ========================================================================
    # BUY ORDERS
    # ========================================================================
    
    def buy(
        self,
        symbol: str,
        shares: float,
        price: float,
        reason: str = ''
    ) -> bool:
        """
        Execute simulated buy order.
        
        Args:
            symbol: Stock ticker
            shares: Number of shares
            price: Buy price
            reason: Trade reason/signal
            
        Returns:
            True if successful, False if insufficient funds
        """
        cost = shares * price
        
        # Check balance
        if cost > self.balance:
            print(f"❌ Insufficient funds: Need ${cost:.2f}, Have ${self.balance:.2f}")
            return False
        
        # Update or create position
        if symbol in self.positions:
            # Add to existing position (average price)
            old_shares = self.positions[symbol]['shares']
            old_avg = self.positions[symbol]['avg_price']
            total_cost = (old_shares * old_avg) + cost
            total_shares = old_shares + shares
            
            self.positions[symbol] = {
                'shares': total_shares,
                'avg_price': total_cost / total_shares,
                'entry_date': self.positions[symbol]['entry_date'],
                'current_price': price
            }
        else:
            # New position
            self.positions[symbol] = {
                'shares': shares,
                'avg_price': price,
                'entry_date': datetime.now(),
                'current_price': price
            }
        
        # Update balance
        self.balance -= cost
        
        # Log trade
        self.trade_history.append({
            'type': 'BUY',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'cost': cost,
            'date': datetime.now().isoformat(),
            'reason': reason
        })
        
        print(f"✓ PAPER BUY: {shares} {symbol} @ ${price:.2f} = ${cost:.2f}")
        print(f"  Balance: ${self.balance:.2f}")
        
        return True
    
    # ========================================================================
    # SELL ORDERS
    # ========================================================================
    
    def sell(
        self,
        symbol: str,
        shares: float,
        price: float,
        reason: str = ''
    ) -> bool:
        """
        Execute simulated sell order.
        
        Args:
            symbol: Stock ticker
            shares: Number of shares to sell
            price: Sell price
            reason: Trade reason
            
        Returns:
            True if successful, False if position not found or insufficient shares
        """
        # Check if holding position
        if symbol not in self.positions:
            print(f"❌ Not holding {symbol}")
            return False
        
        pos = self.positions[symbol]
        
        # Check share quantity
        if shares > pos['shares']:
            print(f"❌ Insufficient shares: Have {pos['shares']}, want to sell {shares}")
            return False
        
        # Calculate P&L
        proceeds = shares * price
        entry_cost = shares * pos['avg_price']
        pnl = proceeds - entry_cost
        pnl_pct = (price - pos['avg_price']) / pos['avg_price'] * 100
        
        # Update balance
        self.balance += proceeds
        
        # Update position
        pos['shares'] -= shares
        if pos['shares'] == 0:
            del self.positions[symbol]
        
        # Log trade
        self.trade_history.append({
            'type': 'SELL',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'proceeds': proceeds,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'date': datetime.now().isoformat(),
            'reason': reason
        })
        
        # Print result
        emoji = "✅" if pnl > 0 else "❌" if pnl < 0 else "⚪"
        print(f"{emoji} PAPER SELL: {shares} {symbol} @ ${price:.2f}")
        print(f"  P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
        print(f"  Balance: ${self.balance:.2f}")
        
        return True
    
    # ========================================================================
    # ACCOUNT STATE
    # ========================================================================
    
    def get_balance(self) -> float:
        """Get current cash balance."""
        return self.balance
    
    def get_positions(self) -> Dict[str, Dict]:
        """Get current open positions."""
        return self.positions.copy()
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get specific position."""
        return self.positions.get(symbol)
    
    def get_total_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate total portfolio value (cash + positions).
        
        Args:
            current_prices: Dict of symbol -> current price
            
        Returns:
            Total portfolio value
        """
        total = self.balance
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                total += pos['shares'] * current_prices[symbol]
        return total
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    def print_summary(self) -> None:
        """Print account summary."""
        print("\n" + "="*60)
        print("PAPER TRADING ACCOUNT SUMMARY")
        print("="*60)
        print(f"Starting Balance: ${self.starting_balance:.2f}")
        print(f"Current Balance:  ${self.balance:.2f}")
        print(f"Change:           ${self.balance - self.starting_balance:+.2f}")
        print(f"Return:           {(self.balance / self.starting_balance - 1) * 100:+.2f}%")
        print()
        
        if self.positions:
            print("OPEN POSITIONS:")
            print("-"*60)
            for symbol, pos in self.positions.items():
                print(f"{symbol}: {pos['shares']} shares @ ${pos['avg_price']:.2f} avg")
            print()
        
        if len(self.trade_history) > 0:
            print(f"TRADES EXECUTED: {len(self.trade_history)}")
            buys = sum(1 for t in self.trade_history if t['type'] == 'BUY')
            sells = sum(1 for t in self.trade_history if t['type'] == 'SELL')
            print(f"  Buys: {buys} | Sells: {sells}")
        
        print("="*60 + "\n")
    
    def get_trade_history(self) -> List[Dict]:
        """Get complete trade history."""
        return self.trade_history.copy()
