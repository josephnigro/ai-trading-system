# ==============================
# DIAGNOSTIC TEST - Show What Gets Filtered
# ==============================

from production_system import ProductionTradingSystem
from datetime import datetime

TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
    'NVDA', 'TSLA', 'JNJ', 'V', 'WMT',
    'JPM', 'PG', 'MA', 'HD', 'DIS',
]

def main():
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC TEST - SIGNAL GENERATION & FILTERING")
    print("="*80 + "\n")
    
    system = ProductionTradingSystem()
    system.scanner.tickers = TICKERS
    
    print(f"Scanning {len(TICKERS)} stocks...\n")
    
    # Run scan (no filtering yet)
    from Scanner import AITradingScanner
    scanner = AITradingScanner(tickers=TICKERS)
    results = scanner.scan(period="1y")
    
    print(f"\n{'='*80}")
    print(f"BEFORE FILTERING: {len(results)} signals generated")
    print(f"{'='*80}\n")
    
    # Show all signals before filtering
    if results:
        print("Signal Breakdown (BEFORE Filter):")
        buy = [r for r in results if r['signal'] == 'BUY']
        sell = [r for r in results if r['signal'] == 'SELL']
        hold = [r for r in results if r['signal'] == 'HOLD']
        
        print(f"  BUY:  {len(buy)}")
        print(f"  SELL: {len(sell)}")
        print(f"  HOLD: {len(hold)}\n")
        
        # Show sample signals
        print("Sample signals (before filtering):")
        for i, signal in enumerate(results[:5], 1):
            print(f"\n  {i}. {signal['ticker']}")
            print(f"     Price: ${signal['price']:.2f}")
            print(f"     Signal: {signal['signal']}")
            print(f"     RSI: {signal['technical'].get('rsi', 'N/A'):.1f}")
            print(f"     MACD: {signal['technical'].get('macd_trend', 'N/A')}")
            print(f"     MA Trend: {signal['technical'].get('ma_trend', 'N/A')}")
    
    # Now apply filter
    print(f"\n{'='*80}")
    print("APPLYING FILTER...")
    print(f"{'='*80}\n")
    
    filtered_results, filtered_out = system.signal_filter.filter_signals(results)
    
    print(f"\nAFTER FILTERING:")
    print(f"  Quality signals: {len(filtered_results)}")
    print(f"  Filtered out: {len(filtered_out)}\n")
    
    if filtered_out:
        print("Why signals were rejected:")
        for ticker, reasons in list(filtered_out.items())[:10]:
            print(f"  {ticker}:")
            for reason in reasons:
                print(f"    - {reason}")
    
    # Show quality signals
    if filtered_results:
        print(f"\n{'='*80}")
        print(f"QUALITY SIGNALS ({len(filtered_results)})")
        print(f"{'='*80}\n")
        
        for signal in filtered_results:
            print(f"{signal['ticker']:<8} {signal['signal']:<6} ${signal['price']:<8.2f} "
                  f"RSI:{signal['technical'].get('rsi', 0):<6.1f}")

if __name__ == "__main__":
    main()
