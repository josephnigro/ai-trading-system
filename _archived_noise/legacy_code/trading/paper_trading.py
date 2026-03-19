"""Paper trading for simulating trades without real money."""

from datetime import datetime


class PaperTradingAccount:
    """Simulates trading account for backtesting and validation."""
    
    def __init__(self, starting_balance=25000):
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.positions = {}
        self.trade_history = []
    
    def buy(self, ticker, shares, price, reason=''):
        """Simulate buying shares."""
        cost = shares * price
        
        if cost > self.balance:
            print(f"❌ Insufficient funds: Need ${cost:.2f}, Have ${self.balance:.2f}")
            return False
        
        if ticker in self.positions:
            old_shares = self.positions[ticker]['shares']
            old_avg = self.positions[ticker]['avg_price']
            
            total_cost = (old_shares * old_avg) + cost
            total_shares = old_shares + shares
            new_avg = total_cost / total_shares
            
            self.positions[ticker] = {
                'shares': total_shares,
                'avg_price': new_avg,
                'entry_date': self.positions[ticker]['entry_date'],
                'current_price': price
            }
        else:
            self.positions[ticker] = {
                'shares': shares,
                'avg_price': price,
                'entry_date': datetime.now(),
                'current_price': price
            }
        
        self.balance -= cost
        
        self.trade_history.append({
            'type': 'BUY',
            'ticker': ticker,
            'shares': shares,
            'price': price,
            'cost': cost,
            'date': datetime.now().isoformat(),
            'reason': reason
        })
        
        print(f"✓ PAPER BUY: {shares} shares of {ticker} @ ${price:.2f} = ${cost:.2f}")
        print(f"  Remaining balance: ${self.balance:.2f}")
        
        return True
    
    def sell(self, ticker, shares, price, reason=''):
        """Simulate selling shares."""
        if ticker not in self.positions:
            print(f"❌ Not holding {ticker}")
            return False
        
        if shares > self.positions[ticker]['shares']:
            print(f"❌ Don't have enough shares")
            return False
        
        proceeds = shares * price
        entry_avg = self.positions[ticker]['avg_price']
        pnl = (price - entry_avg) * shares
        pnl_percent = (price - entry_avg) / entry_avg * 100
        
        self.balance += proceeds
        self.positions[ticker]['shares'] -= shares
        
        if self.positions[ticker]['shares'] == 0:
            del self.positions[ticker]
        
        self.trade_history.append({
            'type': 'SELL',
            'ticker': ticker,
            'shares': shares,
            'price': price,
            'proceeds': proceeds,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'date': datetime.now().isoformat(),
            'reason': reason
        })
        
        emoji = "✅" if pnl > 0 else "❌" if pnl < 0 else "⚪"
        print(f"{emoji} PAPER SELL: {shares} shares of {ticker} @ ${price:.2f}")
        print(f"  P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)")
        print(f"  Balance: ${self.balance:.2f}")
        
        return True
    
    def get_position_value(self, ticker, current_price):
        """Get current value of a position."""
        if ticker not in self.positions:
            return 0
        
        return self.positions[ticker]['shares'] * current_price
    
    def get_portfolio_value(self, current_prices):
        """Get total portfolio value."""
        holdings_value = sum([
            self.get_position_value(ticker, current_prices.get(ticker, self.positions[ticker]['current_price']))
            for ticker in self.positions
        ])
        
        return self.balance + holdings_value
    
    def get_portfolio_report(self, current_prices=None):
        """Get full portfolio report."""
        report = {
            'cash': self.balance,
            'positions': [],
            'total_value': 0,
            'total_pnl': 0,
            'total_pnl_percent': 0
        }
        
        if current_prices is None:
            current_prices = {}
        
        for ticker, pos in self.positions.items():
            current_price = current_prices.get(ticker, pos['current_price'])
            position_value = pos['shares'] * current_price
            entry_value = pos['shares'] * pos['avg_price']
            pnl = position_value - entry_value
            pnl_percent = (pnl / entry_value * 100) if entry_value > 0 else 0
            
            report['positions'].append({
                'ticker': ticker,
                'shares': pos['shares'],
                'entry_price': pos['avg_price'],
                'current_price': current_price,
                'position_value': position_value,
                'pnl': pnl,
                'pnl_percent': pnl_percent
            })
            
            report['total_pnl'] += pnl
        
        report['total_value'] = report['cash'] + sum([p['position_value'] for p in report['positions']])
        report['total_pnl_percent'] = (report['total_pnl'] / self.starting_balance * 100) if self.starting_balance > 0 else 0
        
        return report
    
    def print_portfolio(self, current_prices=None):
        """Print portfolio status."""
        report = self.get_portfolio_report(current_prices)
        
        print("\n" + "="*80)
        print("📊 PAPER TRADING PORTFOLIO")
        print("="*80)
        print(f"Starting Balance: ${self.starting_balance:.2f}")
        print(f"Current Cash: ${report['cash']:.2f}")
        print(f"Total Value: ${report['total_value']:.2f}")
        print(f"Total P&L: ${report['total_pnl']:.2f} ({report['total_pnl_percent']:+.2f}%)")
        print()
        
        if report['positions']:
            print("POSITIONS:")
            for pos in report['positions']:
                emoji = "✅" if pos['pnl'] > 0 else "❌" if pos['pnl'] < 0 else "⚪"
                print(f"{emoji} {pos['ticker']:<8} {pos['shares']:<6} @ ${pos['current_price']:<8.2f} "
                      f"(entry ${pos['entry_price']:.2f}) → ${pos['position_value']:<10.2f} "
                      f"P&L: ${pos['pnl']:>8.2f} ({pos['pnl_percent']:>+6.2f}%)")
        else:
            print("No open positions")
        
        print("="*80 + "\n")
