# ==============================
# RUN SCANNER SCRIPT
# ==============================
# Simple script to run the scanner with options

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from Scanner import AITradingScanner
from dashboard import Dashboard

def main():
    print("\n" + "="*80)
    print("AI TRADING SCANNER - MAIN MENU")
    print("="*80 + "\n")
    
    print("Choose an option:")
    print("1. Scan S&P 500 (all 25 stocks)")
    print("2. Scan custom stocks")
    print("3. Generate dashboard only")
    print("4. Show last results (scanner_results.csv)")
    print("5. Exit")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        print("\nInitializing full S&P 500 scan...")
        scanner = AITradingScanner()  # Use default SP500_TICKERS
        results = scanner.scan(period="1y")
        scanner.print_results(top_n=15)
        
        export_choice = input("\nExport to CSV? (y/n): ").strip().lower()
        if export_choice == 'y':
            scanner.export_to_csv('scanner_results.csv')
        
        viz_choice = input("Generate dashboard? (y/n): ").strip().lower()
        if viz_choice == 'y':
            try:
                dashboard = Dashboard(results)
                dashboard.show()
            except Exception as e:
                print(f"Dashboard generation skipped: {e}")
    
    elif choice == "2":
        tickers_input = input("\nEnter stock tickers (comma-separated, e.g., AAPL,MSFT,GOOGL): ").strip()
        tickers = [t.strip().upper() for t in tickers_input.split(",")]
        
        period = input("Enter period (1d, 5d, 1mo, 3mo, 6mo, 1y) [default: 1y]: ").strip() or "1y"
        
        print(f"\nScanning {len(tickers)} stocks with period {period}...")
        scanner = AITradingScanner(tickers=tickers)
        results = scanner.scan(period=period)
        scanner.print_results(top_n=len(results))
        scanner.export_to_csv('scanner_results.csv')
        
        viz_choice = input("\nGenerate dashboard? (y/n): ").strip().lower()
        if viz_choice == 'y':
            try:
                dashboard = Dashboard(results)
                dashboard.show()
            except Exception as e:
                print(f"Dashboard generation skipped: {e}")
    
    elif choice == "3":
        print("\nLoading previous results...")
        try:
            import pandas as pd
            df = pd.read_csv('scanner_results.csv')
            print(f"Found results for {len(df)} stocks")
            print("\nNote: Dashboard feature requires running a fresh scan first")
        except FileNotFoundError:
            print("No previous results found. Run a scan first!")
    
    elif choice == "4":
        print("\nShowing last scan results...")
        try:
            import pandas as pd
            df = pd.read_csv('scanner_results.csv')
            
            print("\n" + "="*100)
            print("PREVIOUS SCAN RESULTS")
            print("="*100 + "\n")
            
            # Show BUY signals
            buy_df = df[df['Signal'] == 'BUY']
            if len(buy_df) > 0:
                print("BUY SIGNALS:")
                print(buy_df[['Ticker', 'Price', 'Signal', 'RSI', 'MACD_Trend', 'ML_Direction']].to_string(index=False))
                print()
            
            # Show summary
            print("\nSUMMARY:")
            print(f"Total Stocks: {len(df)}")
            print(f"BUY: {len(buy_df)}")
            print(f"SELL: {len(df[df['Signal'] == 'SELL'])}")
            print(f"HOLD: {len(df[df['Signal'] == 'HOLD'])}")
            
        except FileNotFoundError:
            print("No previous results found. Run a scan first using options 1 or 2!")
    
    elif choice == "5":
        print("\nExiting scanner. Goodbye!")
    
    else:
        print("\nInvalid choice. Please try again.")
        main()

if __name__ == "__main__":
    main()
