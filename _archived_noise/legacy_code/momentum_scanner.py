# ==============================
# MOMENTUM SCANNER - HIGH UPSIDE POTENTIAL
# ==============================
# Finds stocks with 8-20%+ upside potential (momentum breakouts)

import pandas as pd
import numpy as np
from datetime import datetime
from data_engine import DataEngine

class MomentumScanner:
    """
    Scans for high-upside momentum stocks
    Looks for: breakouts, volume expansion, relative strength
    """
    
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []
    
    def scan(self, period="1y"):
        """Scan for momentum opportunities"""
        print(f"🔍 Scanning {len(self.tickers)} stocks for momentum...\n")
        
        # Fetch data using Alpha Vantage
        engine = DataEngine(self.tickers)
        data = engine.fetch_data(period=period)
        
        # Analyze each stock
        for ticker in self.tickers:
            if ticker not in data:
                continue
            
            result = self.analyze_momentum(ticker, data[ticker])
            if result:
                self.results.append(result)
        
        # Sort by upside potential
        self.results = sorted(self.results, key=lambda x: x['upside_potential'], reverse=True)
        
        return self.results
    
    def analyze_momentum(self, ticker, df):
        """Analyze a single stock for momentum"""
        
        if len(df) < 50:
            return None
        
        # Current price
        current_price = df['Close'].iloc[-1]
        
        # Recent performance (last 20 days)
        recent_return = (df['Close'].iloc[-1] / df['Close'].iloc[-20] - 1) * 100
        
        # 50-day and 200-day moving averages
        ma50 = df['Close'].rolling(50).mean().iloc[-1]
        ma200 = df['Close'].rolling(200).mean().iloc[-1]
        
        # RSI (14-day)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # Volume trend
        vol_20 = df['Volume'].tail(20).mean()
        vol_50 = df['Volume'].tail(50).mean()
        vol_expansion = (vol_20 / vol_50 - 1) * 100
        
        # 52-week high/low - ensure proper scalar extraction
        high_series = df['High'].tail(252).max()
        low_series = df['Low'].tail(252).min()
        
        # Convert to scalar if needed
        high_52 = float(high_series.iloc[0] if hasattr(high_series, 'iloc') else high_series)
        low_52 = float(low_series.iloc[0] if hasattr(low_series, 'iloc') else low_series)
        
        # How close to 52-week high (breakout indicator)
        from_high = float((current_price / high_52 - 1) * 100)
        from_low = float((current_price / low_52 - 1) * 100)
        
        # Calculate potential upside
        # If stock is near 52-week high with volume + above MA50, likely to move higher
        upside_potential = 0
        
        # Near 52-week high = breakout potential
        if from_high > -5:  # Within 5% of high
            upside_potential += 15
        elif from_high > -15:
            upside_potential += 10
        
        # Above moving averages = uptrend
        if float(current_price) > float(ma50) and float(ma50) > float(ma200):
            upside_potential += 10
        
        # Increasing volume = interest
        if vol_expansion > 10:
            upside_potential += 10
        
        # Recent positive momentum
        if float(recent_return) > 5:
            upside_potential += 10
        elif float(recent_return) > 0:
            upside_potential += 5
        
        # RSI not overbought = room to run
        if float(rsi) < 70:
            upside_potential += 5
        
        # Filter: Only return stocks with potential
        if upside_potential < 15:
            return None
        
        return {
            'ticker': ticker,
            'price': current_price,
            'upside_potential': upside_potential,
            'recent_return': recent_return,
            'rsi': rsi,
            'volume_expansion': vol_expansion,
            'ma50': ma50,
            'ma200': ma200,
            'from_high': from_high,
            'from_low': from_low,
            '52week_high': high_52,
            '52week_low': low_52
        }

def main():
    # Top momentum stocks to scan
    MOMENTUM_TICKERS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
        'NVDA', 'TSLA', 'JNJ', 'V', 'WMT',
        'JPM', 'PG', 'MA', 'HD', 'DIS',
        'PYPL', 'COST', 'NFLX', 'CSCO', 'PEP',
        'ADBE', 'CMCSA', 'INTC', 'AMGN', 'GE',
        'CVX', 'XOM', 'KO', 'MRK', 'VZ',
        'MCD', 'CRM', 'ACN', 'IBM', 'DOW',
        'INTU', 'TXN', 'PM', 'BA', 'GILD',
        'BKNG', 'CHTR', 'AVGO', 'ABBV', 'QCOM',
    ]
    
    print("\n" + "="*100)
    print("🚀 MOMENTUM SCANNER - HIGH UPSIDE POTENTIAL")
    print("="*100 + "\n")
    
    print(f"Scanning {len(MOMENTUM_TICKERS)} stocks for momentum breakouts...\n")
    
    scanner = MomentumScanner(MOMENTUM_TICKERS)
    results = scanner.scan(period="1y")
    
    print(f"\n{'='*100}")
    print(f"📊 RESULTS: {len(results)} MOMENTUM OPPORTUNITIES FOUND")
    print(f"{'='*100}\n")
    
    if results:
        print(f"{'Ticker':<8} {'Price':<10} {'Upside':<10} {'Recent %':<12} {'RSI':<8} {'Vol Exp %':<12} {'From High':<12}")
        print("-" * 100)
        
        for i, stock in enumerate(results, 1):
            print(f"{stock['ticker']:<8} ${stock['price']:<9.2f} {stock['upside_potential']:<10.0f} "
                  f"{stock['recent_return']:<11.1f}% {stock['rsi']:<7.1f} "
                  f"{stock['volume_expansion']:<11.1f}% {stock['from_high']:<11.1f}%")
        
        print("\n" + "="*100)
        print("🎯 TOP 5 OPPORTUNITIES FOR $300 TRADING ACCOUNT")
        print("="*100 + "\n")
        
        for i, stock in enumerate(results[:5], 1):
            # Calculate shares you can buy with $300
            shares_you_can_buy = int(300 / stock['price'])
            investment = shares_you_can_buy * stock['price']
            
            # Potential profit at different upside levels
            profit_10pct = investment * 0.10
            profit_20pct = investment * 0.20
            
            print(f"{i}. {stock['ticker']} - ${stock['price']:.2f}")
            print(f"   Upside Score: {stock['upside_potential']:.0f}/50")
            print(f"   Recent Momentum: {stock['recent_return']:.1f}%")
            print(f"   RSI: {stock['rsi']:.1f} (momentum strength)")
            print(f"   Distance from 52-week high: {stock['from_high']:.1f}%")
            print(f"\n   💵 With $300 capital:")
            print(f"      Can buy: {shares_you_can_buy} shares = ${investment:.2f}")
            print(f"      10% gain = ${profit_10pct:.2f}")
            print(f"      20% gain = ${profit_20pct:.2f}")
            print()
    else:
        print("❌ No momentum stocks found with current thresholds")
        print("   (This is normal on slow market days - try again tomorrow!)\n")

if __name__ == "__main__":
    main()
