# ==============================
# RISK MANAGEMENT MODULE
# ==============================

class RiskManager:
    """
    Manages position sizing, risk allocation, and trade parameters
    Ensures no trade exceeds 1% account risk
    """
    
    def __init__(self, account_size, risk_per_trade=0.01, max_position_size=0.05):
        """
        account_size: Total trading account size in dollars
        risk_per_trade: Risk per trade as % of account (default: 1%)
        max_position_size: Max position as % of account (default: 5%)
        """
        self.account_size = account_size
        self.risk_per_trade = risk_per_trade  # 1%
        self.max_position_size = max_position_size  # 5%
        self.max_risk_dollars = account_size * risk_per_trade
        self.available_capital = account_size
        self.open_positions = {}  # ticker -> position details
    
    def calculate_position_size(self, entry_price, stop_loss_price):
        """
        Calculate position size based on entry, stop loss, and risk per trade
        
        Returns:
        - shares: Number of shares to buy
        - risk_dollars: Actual risk in dollars
        - position_value: Total position value
        """
        
        if entry_price <= 0 or stop_loss_price is None:
            return 0, 0, 0
        
        # Don't allow stop loss above entry price
        if stop_loss_price >= entry_price:
            print(f"Warning: Stop loss must be below entry price")
            return 0, 0, 0
        
        # Risk per share
        risk_per_share = entry_price - stop_loss_price
        
        # Max shares based on 1% account risk
        max_shares_by_risk = self.max_risk_dollars / risk_per_share
        
        # Max position value (5% of account)
        max_position_value = self.account_size * self.max_position_size
        max_shares_by_size = max_position_value / entry_price
        
        # Use the smaller of the two
        shares = int(min(max_shares_by_risk, max_shares_by_size))
        
        if shares <= 0:
            return 0, 0, 0
        
        risk_dollars = shares * risk_per_share
        position_value = shares * entry_price
        
        return shares, risk_dollars, position_value
    
    def calculate_targets(self, entry_price, stop_loss_price, reward_to_risk=1.5):
        """
        Calculate take profit targets for swing trading (not day trading)
        
        reward_to_risk: 1.5 means 1.5x return on risk
        For swing trading, we target 8-15% returns, not 2-4%
        """
        
        risk = entry_price - stop_loss_price
        
        # Target 1: Quick 8% (short-term pop)
        # Target 2: Medium 12% (2-5 day hold)
        # Target Full: 15% (full swing trade, 5-15 day hold)
        
        return {
            'target_1': entry_price * 1.08,        # 8% quick profit
            'target_2': entry_price * 1.12,        # 12% medium term (3-7 days)
            'target_full': entry_price * 1.15,     # 15% full swing (5-15 days)
            'estimated_hold_days': {
                'target_1': '1-2 days',
                'target_2': '3-7 days',
                'target_full': '5-15 days'
            }
        }
    
    def validate_trade(self, ticker, entry_price, stop_loss_price, quantity):
        """
        Validate a trade before execution
        Returns True if safe, False otherwise
        """
        
        # Check if already in similar position
        if ticker in self.open_positions:
            print(f"⚠️  Already have open position in {ticker}")
            return False
        
        # Check risk
        risk = entry_price - stop_loss_price
        if risk <= 0:
            print(f"⚠️  Invalid stop loss for {ticker}")
            return False
        
        # Check position value doesn't exceed max
        position_value = entry_price * quantity
        if position_value > self.account_size * self.max_position_size:
            print(f"⚠️  Position size exceeds 5% limit for {ticker}")
            return False
        
        # Check total risk doesn't exceed 1% account
        risk_dollars = quantity * risk
        if risk_dollars > self.max_risk_dollars:
            print(f"⚠️  Risk exceeds 1% account limit for {ticker}")
            return False
        
        # Check capital available
        if position_value > self.available_capital:
            print(f"⚠️  Insufficient capital for {ticker}")
            return False
        
        return True
    
    def record_position(self, ticker, entry_price, stop_loss, target, shares, risk_dollars):
        """
        Record an open position
        """
        self.open_positions[ticker] = {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target': target,
            'shares': shares,
            'risk_dollars': risk_dollars,
            'position_value': entry_price * shares,
            'status': 'OPEN'
        }
        
        # Reduce available capital
        self.available_capital -= (entry_price * shares)
    
    def close_position(self, ticker, exit_price, reason='unknown'):
        """
        Close a position and record P&L
        """
        if ticker not in self.open_positions:
            print(f"No open position for {ticker}")
            return None
        
        pos = self.open_positions[ticker]
        entry = pos['entry_price']
        shares = pos['shares']
        
        # Calculate P&L
        pnl_dollars = (exit_price - entry) * shares
        pnl_percent = (exit_price - entry) / entry * 100
        
        # Return capital
        self.available_capital += (exit_price * shares)
        
        # Mark as closed
        pos['status'] = 'CLOSED'
        pos['exit_price'] = exit_price
        pos['exit_reason'] = reason
        pos['pnl_dollars'] = pnl_dollars
        pos['pnl_percent'] = pnl_percent
        
        return {
            'ticker': ticker,
            'pnl_dollars': pnl_dollars,
            'pnl_percent': pnl_percent,
            'reason': reason
        }
    
    def get_portfolio_status(self):
        """
        Get current portfolio status
        """
        open_positions = {k: v for k, v in self.open_positions.items() if v['status'] == 'OPEN'}
        
        total_risk = sum([pos['risk_dollars'] for pos in open_positions.values()])
        total_position_value = sum([pos['position_value'] for pos in open_positions.values()])
        
        return {
            'account_size': self.account_size,
            'available_capital': self.available_capital,
            'open_positions': len(open_positions),
            'total_position_value': total_position_value,
            'total_risk_dollars': total_risk,
            'total_risk_percent': (total_risk / self.account_size) * 100 if self.account_size > 0 else 0,
            'positions': open_positions
        }
