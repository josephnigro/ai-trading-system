"""Risk management for position sizing and trade validation."""


class RiskManager:
    """Manages position sizing ensuring 1% risk per trade."""
    
    def __init__(self, account_size, risk_per_trade=0.01, max_position_size=0.05):
        self.account_size = account_size
        self.risk_per_trade = risk_per_trade
        self.max_position_size = max_position_size
        self.max_risk_dollars = account_size * risk_per_trade
        self.available_capital = account_size
        self.open_positions = {}
    
    def calculate_position_size(self, entry_price, stop_loss_price):
        """Calculate position size based on entry and stop loss."""
        if entry_price <= 0 or stop_loss_price is None:
            return 0, 0, 0
        
        if stop_loss_price >= entry_price:
            return 0, 0, 0
        
        risk_per_share = entry_price - stop_loss_price
        max_shares_by_risk = self.max_risk_dollars / risk_per_share
        max_position_value = self.account_size * self.max_position_size
        max_shares_by_size = max_position_value / entry_price
        
        shares = int(min(max_shares_by_risk, max_shares_by_size))
        
        if shares <= 0:
            return 0, 0, 0
        
        risk_dollars = shares * risk_per_share
        position_value = shares * entry_price
        
        return shares, risk_dollars, position_value
    
    def calculate_targets(self, entry_price, stop_loss_price, reward_to_risk=2.0):
        """Calculate take profit targets based on reward-to-risk ratio."""
        risk = entry_price - stop_loss_price
        profit_target = entry_price + (risk * reward_to_risk)
        
        return {
            'target_1': entry_price + (risk * 0.5),
            'target_2': entry_price + (risk * 1.0),
            'target_full': profit_target,
        }
    
    def validate_trade(self, ticker, entry_price, stop_loss_price, quantity):
        """Validate a trade before execution."""
        if ticker in self.open_positions:
            return False
        
        risk = entry_price - stop_loss_price
        if risk <= 0:
            return False
        
        position_value = entry_price * quantity
        if position_value > self.account_size * self.max_position_size:
            return False
        
        risk_dollars = quantity * risk
        if risk_dollars > self.max_risk_dollars:
            return False
        
        if position_value > self.available_capital:
            return False
        
        return True
    
    def record_position(self, ticker, entry_price, stop_loss, target, shares, risk_dollars):
        """Record an open position."""
        self.open_positions[ticker] = {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target': target,
            'shares': shares,
            'risk_dollars': risk_dollars,
            'position_value': entry_price * shares,
            'status': 'OPEN'
        }
        self.available_capital -= (entry_price * shares)
    
    def close_position(self, ticker, exit_price, reason='unknown'):
        """Close a position and record P&L."""
        if ticker not in self.open_positions:
            return None
        
        pos = self.open_positions[ticker]
        entry = pos['entry_price']
        shares = pos['shares']
        
        pnl_dollars = (exit_price - entry) * shares
        pnl_percent = (exit_price - entry) / entry * 100
        
        self.available_capital += (exit_price * shares)
        
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
        """Get current portfolio status."""
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
