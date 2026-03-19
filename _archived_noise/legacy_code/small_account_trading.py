# ==============================
# PAPER TRADING WITH $300 CAPITAL
# ==============================
# Find momentum stocks, buy signals, auto-sell at 10-20% targets

from momentum_scanner import MomentumScanner
from paper_trading import PaperTradingAccount
from datetime import datetime
from data_engine import DataEngine

class SmallCapTradingBot:
    """
    Paper trading bot for $300 account
    - Finds momentum stocks
    - You approve entries
    - Auto-sells at 10-20% profit targets
    """
    
    def __init__(self, capital=300, profit_target_percent=15):
        self.account = PaperTradingAccount(starting_balance=capital)
        self.profit_target = profit_target_percent
        self.capital = capital
        self.trade_history = []
    
    def find_opportunities(self, tickers):
        """Find momentum stocks"""
        print("🔍 Finding momentum stocks...\n")
        
        scanner = MomentumScanner(tickers)
        opportunities = scanner.scan(period="1y")
        
        return opportunities
    
    def calculate_position_size(self, stock_price):
        """How many shares to buy with $300"""
        # Risk 25% of account per trade ($75)
        risk_amount = self.capital * 0.25
        
        # Simple: stop loss 5% below entry
        shares = int(risk_amount / (stock_price * 0.05))
        
        # But cap by what we can afford
        max_affordable = int(self.capital * 0.25 / stock_price)  # Use 25% of capital
        
        shares = min(shares, max_affordable)
        return max(1, shares)
    
    def execute_trade(self, ticker, entry_price, shares, target_pct):
        """Execute a paper trade"""
        cost = entry_price * shares
        target_price = entry_price * (1 + target_pct / 100)
        stop_loss = entry_price * 0.95  # 5% stop loss
        
        print(f"\n{'='*60}")
        print(f"📊 TRADE SETUP: {ticker}")
        print(f"{'='*60}")
        print(f"Entry Price: ${entry_price:.2f}")
        print(f"Shares: {shares}")
        print(f"Position Size: ${cost:.2f}")
        print(f"Stop Loss: ${stop_loss:.2f}")
        print(f"Target: ${target_price:.2f} ({target_pct}% gain = ${cost * (target_pct/100):.2f})")
        print(f"Risk: ${cost - (shares * stop_loss):.2f}")
        print(f"{'='*60}")
        
        # Get approval
        while True:
            response = input("\nBUY THIS STOCK? (yes/no/skip): ").strip().lower()
            if response in ['yes', 'y']:
                break
            elif response in ['no', 'n', 'skip', 's']:
                print(f"❌ Trade skipped")
                return False
            else:
                print("Enter: yes, no, or skip")
        
        # Execute buy
        success = self.account.buy(ticker, shares, entry_price, f"Momentum entry - target {target_pct}%")
        
        if success:
            self.trade_history.append({
                'ticker': ticker,
                'entry': entry_price,
                'shares': shares,
                'target': target_price,
                'stop': stop_loss,
                'target_pct': target_pct,
                'entry_time': datetime.now()
            })
        
        return success
    
    def monitor_positions(self):
        """Check if any positions hit targets"""
        print("\n" + "="*60)
        print("📈 MONITORING OPEN POSITIONS")
        print("="*60 + "\n")
        
        open_positions = self.account.positions.copy()
        
        if not open_positions:
            print("No open positions\n")
            return
        
        # Get current prices for all tickers
        engine = DataEngine(list(open_positions.keys()))
        engine.fetch_data(period="1d")
        
        for ticker in open_positions:
            pos = open_positions[ticker]
            
            # Get current price from Alpha Vantage
            try:
                current_price = engine.get_latest_price(ticker)
                if current_price is None:
                    print(f"Could not fetch price for {ticker}\n")
                    continue
            except:
                print(f"Could not fetch price for {ticker}\n")
                continue
            
            current_price = float(current_price)
            entry = pos['avg_price']
            return_pct = (current_price - entry) / entry * 100
            current_value = current_price * pos['shares']
            entry_value = entry * pos['shares']
            pnl = current_value - entry_value
            
            print(f"{ticker}:")
            print(f"  Entry: ${entry:.2f} → Current: ${current_price:.2f}")
            print(f"  Return: {return_pct:+.2f}%")
            print(f"  P&L: ${pnl:+.2f}")
            print()
            
            # Check if target hit
            for trade in self.trade_history:
                if trade['ticker'] == ticker and ticker in self.account.positions:
                    if current_price >= trade['target']:
                        print(f"🎯 TARGET HIT! {ticker} reached ${current_price:.2f}")
                        response = input("SELL NOW? (yes/no): ").strip().lower()
                        if response in ['yes', 'y']:
                            self.account.sell(ticker, pos['shares'], current_price, 
                                            f"Target {trade['target_pct']}% hit")
                            print(f"✅ SOLD: {ticker}")
                    
                    # Check if stop loss hit
                    elif current_price <= trade['stop']:
                        print(f"🛑 STOP LOSS HIT! {ticker} dropped to ${current_price:.2f}")
                        response = input("SELL NOW? (yes/no): ").strip().lower()
                        if response in ['yes', 'y']:
                            self.account.sell(ticker, pos['shares'], current_price, 
                                            f"Stop loss {trade['stop']:.2f} hit")
                            print(f"✅ SOLD: {ticker}")
    
    def print_summary(self):
        """Print trading summary"""
        self.account.print_portfolio()
        
        # Show trade history
        if self.trade_history:
            print("\n" + "="*60)
            print("📊 TRADING LOG")
            print("="*60)
            for trade in self.trade_history:
                print(f"{trade['ticker']}: {trade['shares']} @ ${trade['entry']:.2f} → Target ${trade['target']:.2f}")

def main():
    print("\n" + "🚀"*30)
    print("SMALL ACCOUNT PAPER TRADING - $300 CAPITAL")
    print("🚀"*30 + "\n")
    
    # Initialize
    bot = SmallCapTradingBot(capital=300, profit_target_percent=15)
    print(f"Starting Capital: ${bot.capital:.2f}\n")
    
    # Find opportunities
    TICKERS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
        'NVDA', 'TSLA', 'JNJ', 'V', 'WMT',
        'JPM', 'PG', 'MA', 'HD', 'DIS',
        'PYPL', 'COST', 'NFLX', 'CSCO', 'PEP',
        'ADBE', 'CMCSA', 'INTC', 'AMGN', 'GE',
    ]
    
    opportunities = bot.find_opportunities(TICKERS)
    
    if not opportunities:
        print("\n❌ No momentum stocks found today")
        return
    
    # Show top opportunities
    print(f"\n{'='*60}")
    print(f"TOP OPPORTUNITIES FOR $300 ACCOUNT")
    print(f"{'='*60}\n")
    
    for i, opp in enumerate(opportunities[:5], 1):
        shares = bot.calculate_position_size(opp['price'])
        investment = shares * opp['price']
        potential_gain = investment * (15 / 100)
        
        print(f"{i}. {opp['ticker']} - ${opp['price']:.2f}")
        print(f"   Momentum Score: {opp['upside_potential']:.0f}/50")
        print(f"   Recent Return: {opp['recent_return']:.1f}%")
        print(f"   Shares you can buy: {shares} = ${investment:.2f}")
        print(f"   Potential profit at 15% gain: ${potential_gain:.2f}\n")
    
    # Ask user which to trade
    print(f"{'='*60}\n")
    while True:
        choice = input("Which stock do you want to trade? (enter ticker or 'quit'): ").strip().upper()
        
        if choice == 'QUIT':
            break
        
        # Find the opportunity
        selected = next((o for o in opportunities if o['ticker'] == choice), None)
        
        if not selected:
            print(f"❌ {choice} not in list")
            continue
        
        # Calculate position
        shares = bot.calculate_position_size(selected['price'])
        
        # Execute trade
        success = bot.execute_trade(
            selected['ticker'],
            selected['price'],
            shares,
            15  # 15% target
        )
        
        if success:
            print(f"✅ BUY ORDER EXECUTED")
    
    # Show final status
    bot.print_summary()

if __name__ == "__main__":
    main()
