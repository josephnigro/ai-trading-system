# ==============================
# INTERACTIVE STRESS TEST - 50 STOCKS WITH TRADES
# ==============================
# Full trading session - you approve each signal

from production_system import ProductionTradingSystem

# Top 50 S&P 500 stocks by market cap
EXPANDED_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
    'NVDA', 'TSLA', 'BRK.B', 'JNJ', 'V',
    'WMT', 'JPM', 'PG', 'MA', 'HD',
    'DIS', 'PYPL', 'COST', 'NFLX', 'CSCO',
    'PEP', 'ADBE', 'CMCSA', 'INTC', 'AMGN',
    'GE', 'CVX', 'XOM', 'KO', 'MRK',
    'VZ', 'MCD', 'CRM', 'ACN', 'IBM',
    'DOW', 'INTU', 'TXN', 'PM', 'BA',
    'GILD', 'BKNG', 'CHTR', 'AVGO', 'ABBV',
    'QCOM', 'PCAR', 'AXP', 'AMD', 'SBUX'
]

def main():
    print("\n" + "🔥"*40)
    print("INTERACTIVE STRESS TEST - 50 STOCKS WITH LIVE APPROVALS")
    print("🔥"*40 + "\n")
    
    # Initialize
    system = ProductionTradingSystem()
    system.scanner.tickers = EXPANDED_TICKERS
    
    # Run full session
    print(f"Scanning {len(EXPANDED_TICKERS)} stocks and waiting for YOUR approval...\n")
    system.run_session(period="1y")

if __name__ == "__main__":
    main()
