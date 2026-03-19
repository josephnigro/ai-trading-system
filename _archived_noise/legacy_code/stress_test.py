# ==============================
# STRESS TEST - LARGE UNIVERSE
# ==============================
# Tests system with 50+ stocks to stress test scanning and analysis

from production_system import ProductionTradingSystem
from datetime import datetime

# Expanded stock list - S&P 500 top 50
EXPANDED_TICKERS = [
    # Top 25 (original)
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
    'NVDA', 'TSLA', 'BRK.B', 'JNJ', 'V',
    'WMT', 'JPM', 'PG', 'MA', 'HD',
    'DIS', 'PYPL', 'COST', 'nflx', 'CSCO',
    'PEP', 'ADBE', 'CMCSA', 'INTC', 'AMGN',
    
    # Additional 25
    'GE', 'CVX', 'XOM', 'KO', 'MRK',
    'VZ', 'MCD', 'CRM', 'ACN', 'IBM',
    'DOW', 'INTU', 'TXN', 'PM', 'BA',
    'GILD', 'BKNG', 'CHTR', 'AVGO', 'ABBV',
    'QCOM', 'PCAR', 'AXP', 'AMD', 'SBUX'
]

def main():
    print("\n" + "="*80)
    print("🔥 PRODUCTION SYSTEM STRESS TEST - 50 STOCKS")
    print("="*80 + "\n")
    
    print("Initializing system with EXPANDED stock universe...\n")
    
    # Create system
    system = ProductionTradingSystem()
    
    # Override the tickers with our expanded list
    system.scanner.tickers = EXPANDED_TICKERS
    print(f"✓ Loaded {len(EXPANDED_TICKERS)} stocks for scanning\n")
    
    # Run pre-flight
    print("Running pre-flight safety checks...")
    if not system.pre_flight_check():
        print("Pre-flight failed")
        return
    
    # Run the scan
    print(f"⏰ Starting scan at {datetime.now().strftime('%H:%M:%S')}\n")
    start_time = datetime.now()
    
    signals = system.run_scan(period="1y")
    
    scan_time = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Scan completed in {scan_time:.1f} seconds")
    print(f"   Rate: {len(EXPANDED_TICKERS) / scan_time:.1f} stocks/second")
    print(f"   Quality signals: {len(signals)}\n")
    
    # Show signal breakdown
    if signals:
        buy_signals = [s for s in signals if s['signal'] == 'BUY']
        sell_signals = [s for s in signals if s['signal'] == 'SELL']
        hold_signals = [s for s in signals if s['signal'] == 'HOLD']
        
        print(f"Signal Breakdown:")
        print(f"  BUY:  {len(buy_signals)}")
        print(f"  SELL: {len(sell_signals)}")
        print(f"  HOLD: {len(hold_signals)}\n")
        
        # Show the top BUY signals
        if buy_signals:
            print("Top Buy Signals:")
            buy_signals = sorted(buy_signals, key=lambda x: x['technical']['score'], reverse=True)
            for i, signal in enumerate(buy_signals[:5], 1):
                print(f"  {i}. {signal['ticker']:<8} ${signal['price']:<8.2f} "
                      f"RSI:{signal['technical']['rsi']:<6.1f} "
                      f"Tech:{signal['technical']['score']:+.1f}")
    
    # Print portfolio status
    print("\nSystem Status:")
    status = system.risk_manager.get_portfolio_status()
    print(f"  Account: ${status['account_size']:.2f}")
    print(f"  Available Capital: ${status['available_capital']:.2f}")
    print(f"  Open Positions: {status['open_positions']}")
    print(f"  Max Daily Risk: ${status['account_size'] * 0.02:.2f}")
    
    print("\n" + "="*80)
    print("✅ STRESS TEST COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
