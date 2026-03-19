"""Consolidated system tests suite."""

from tests import SystemTests


def stress_test():
    """Run stress test with 50 stocks."""
    print("\n" + "="*60)
    print("STRESS TEST: 50 Stocks")
    print("="*60 + "\n")
    
    tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
        'NVDA', 'TSLA', 'BRK.B', 'JNJ', 'V',
        'WMT', 'JPM', 'PG', 'MA', 'HD',
        'DIS', 'PYPL', 'COST', 'NFLX', 'CSCO',
        'PEP', 'ADBE', 'CMCSA', 'INTC', 'AMGN',
        'GE', 'CVX', 'XOM', 'KO', 'MRK',
        'VZ', 'MCD', 'CRM', 'ACN', 'IBM',
        'DOW', 'INTU', 'TXN', 'PM', 'BA',
        'GILD', 'BKNG', 'CHTR', 'AVGO', 'ABBV',
        'QCOM', 'LLY', 'AXP', 'HON', 'CAT'
    ]
    
    from core.scanner import Scanner
    
    scanner = Scanner(tickers)
    results = scanner.scan(period="1y", mode="ai")
    scanner.print_results()
    
    print(f"✓ Stress test completed: {len(results)} stocks analyzed")


def interactive_test():
    """Interactive testing mode."""
    print("\n" + "="*60)
    print("INTERACTIVE TEST MODE")
    print("="*60 + "\n")
    
    print("1. Test Scanner (AI Mode)")
    print("2. Test Scanner (Momentum Mode)")
    print("3. Run Stress Test (50 stocks)")
    print("4. Run All Unit Tests")
    print("5. Exit\n")
    
    choice = input("Select test (1-5): ").strip()
    
    if choice == "1":
        SystemTests.test_scanner_ai_mode()
    elif choice == "2":
        SystemTests.test_scanner_momentum_mode()
    elif choice == "3":
        stress_test()
    elif choice == "4":
        SystemTests.run_all()
    elif choice == "5":
        print("Exiting...")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "stress":
            stress_test()
        elif sys.argv[1] == "interactive":
            interactive_test()
        elif sys.argv[1] == "all":
            SystemTests.run_all()
    else:
        SystemTests.run_all()
