#!/usr/bin/env python3
"""
AI TRADING SCANNER - TEST MODE
Uses smaller stock list to fit within Alpha Vantage free tier (25 requests/day)
Full list requires premium plan or yfinance fallback
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import pandas as pd
from datetime import datetime
from data_engine import DataEngine
from technical_analysis import TechnicalAnalyzer
from ml_predictor import MLPredictor
from sentiment_analyzer import SentimentAnalyzer

class AITradingScanner:
    """
    Complete AI Trading Scanner (Test Mode)
    Uses only 10 stocks to fit Alpha Vantage free tier
    """
    
    # Test list (10 stocks - fits within 25/day free tier)
    TEST_TICKERS = [
        'GME', 'AMC', 'BBBY', 'SOFI', 'PLTR',
        'LCID', 'NIO', 'CLOV', 'OCGN', 'SPCE'
    ]
    
    # Full list (30 stocks - requires premium or yfinance fallback)
    FULL_TICKERS = [
        'GME', 'AMC', 'BBBY', 'RIDE', 'SOFI', 'PLTR', 'LCID', 'NIO',
        'WISH', 'CLOV', 'CLNE', 'OCGN', 'SPCE', 'NVAX', 'RIOT', 'TLRY',
        'SNDL', 'PROG', 'ATER', 'GNUS', 'CIDM', 'BLNK', 'FUBO', 'PRPL',
        'RIG', 'UXIN', 'KODK', 'BNGO', 'IDEX', 'VROOM'
    ]
    
    def __init__(self, tickers=None, test_mode=True):
        if tickers is None:
            tickers = self.TEST_TICKERS if test_mode else self.FULL_TICKERS
        
        self.tickers = tickers
        self.results = []
        self.data_engine = DataEngine(tickers)
        self.scan_timestamp = None
    
    def scan(self, period="1y"):
        """
        Run complete scan on all tickers
        """
        print(f"\n{'='*80}")
        print(f"AI TRADING SCANNER - TEST MODE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Scanning {len(self.tickers)} stocks ({period})")
        print(f"{'='*80}\n")
        
        self.scan_timestamp = datetime.now()
        
        # Fetch data
        print("Step 1: Fetching market data...")
        market_data = self.data_engine.fetch_data(period=period, interval="1d")
        print(f"[OK] Data fetched for {len(market_data)} stocks\n")
        
        # Analyze each stock
        print("Step 2: Analyzing stocks...")
        for ticker in self.tickers:
            if ticker not in market_data:
                continue
            
            try:
                print(f"  | Analyzing {ticker}...", end=" ")
                analysis = self.analyze_stock(ticker, market_data[ticker])
                self.results.append(analysis)
                print(" OK")
            except Exception as e:
                print(f" ERROR: {e}")
        
        print(f"\n[OK] Analysis complete for {len(self.results)} stocks\n")
        return self.results
    
    def analyze_stock(self, ticker, data):
        """
        Analyze a single stock with all models
        """
        analysis = {
            'ticker': ticker,
            'timestamp': self.scan_timestamp,
            'price': data['Close'].iloc[-1],
            'date': data.index[-1]
        }
        
        # Technical Analysis
        tech_analyzer = TechnicalAnalyzer(data)
        tech_signals = tech_analyzer.analyze()
        tech_score = tech_analyzer.get_score()
        
        analysis['technical'] = {
            'rsi': tech_signals.get('RSI'),
            'rsi_signal': tech_signals.get('RSI_signal'),
            'macd_trend': tech_signals.get('MACD_trend'),
            'ma_trend': tech_signals.get('MA_trend'),
            'score': tech_score
        }
        
        # ML Prediction
        ml_predictor = MLPredictor(data)
        if ml_predictor.train(lookback_days=20):
            direction, confidence = ml_predictor.predict_direction()
            predicted_change = ml_predictor.get_predicted_price_change()
            
            analysis['ml_prediction'] = {
                'direction': direction,
                'confidence': confidence,
                'predicted_change_pct': predicted_change
            }
        else:
            analysis['ml_prediction'] = {
                'direction': 'UNKNOWN',
                'confidence': 0,
                'predicted_change_pct': 0
            }
        
        # Sentiment Analysis
        sentiment_analyzer = SentimentAnalyzer()
        sentiment = sentiment_analyzer.analyze(data)
        
        analysis['sentiment'] = {
            'overall_score': sentiment['overall_score'],
            'overall_sentiment': sentiment['overall_sentiment'],
            'momentum_sentiment': sentiment['momentum_sentiment'],
            'volume_sentiment': sentiment['volume_sentiment']
        }
        
        # Overall Buy/Sell Signal
        analysis['signal'] = self.generate_signal(analysis)
        
        return analysis
    
    def generate_signal(self, analysis):
        """
        Generate final BUY/SELL/HOLD signal
        """
        tech_score = analysis['technical']['score']
        ml_direction = analysis['ml_prediction']['direction']
        sentiment_score = analysis['sentiment']['overall_score']
        
        # Weighted scoring
        buy_score = 0
        
        # Technical contribution (40%)
        if tech_score > 0:
            buy_score += (tech_score / 5) * 0.4
        
        # ML contribution (40%)
        ml_weight = analysis['ml_prediction']['confidence'] * 0.4
        if ml_direction == 'UP':
            buy_score += ml_weight
        elif ml_direction == 'DOWN':
            buy_score -= ml_weight
        
        # Sentiment contribution (20%)
        if sentiment_score > 0:
            buy_score += (sentiment_score / 1.0) * 0.2
        
        # Generate signal
        if buy_score > 0.15:
            return 'BUY'
        elif buy_score < -0.15:
            return 'SELL'
        else:
            return 'HOLD'
    
    def print_results(self, top_n=10):
        """
        Print top buy signals
        """
        if not self.results:
            print("No results to display. Run scan() first.")
            return
        
        # Sort by signal priority
        buy_stocks = [r for r in self.results if r['signal'] == 'BUY']
        sell_stocks = [r for r in self.results if r['signal'] == 'SELL']
        hold_stocks = [r for r in self.results if r['signal'] == 'HOLD']
        
        print(f"\n{'='*100}")
        timestamp_str = self.scan_timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.scan_timestamp else 'UNKNOWN'
        print(f"SCAN RESULTS - {timestamp_str}")
        print(f"{'='*100}\n")
        
        # BUY signals
        if buy_stocks:
            print(f"{'GREEN BUY SIGNALS':^100}")
            print(f"-{'-'*98}-")
            print(f"{'Ticker':<8} {'Price':<10} {'RSI':<8} {'MACD':<10} {'ML':<10} {'Sentiment':<15}")
            print(f"-{'-'*98}-")
            for stock in buy_stocks[:top_n]:
                tech = stock['technical']
                ml = stock['ml_prediction']
                sent = stock['sentiment']
                print(f"{stock['ticker']:<8} ${stock['price']:<9.2f} {tech['rsi']:<8.1f} "
                      f"{tech['macd_trend']:<10} {ml['direction']:<10} {sent['overall_sentiment']:<15}")
            print()
        
        # SELL signals
        if sell_stocks:
            print(f"{'RED SELL SIGNALS':^100}")
            print(f"-{'-'*98}-")
            print(f"{'Ticker':<8} {'Price':<10} {'RSI':<8} {'MACD':<10} {'ML':<10} {'Sentiment':<15}")
            print(f"-{'-'*98}-")
            for stock in sell_stocks[:top_n]:
                tech = stock['technical']
                ml = stock['ml_prediction']
                sent = stock['sentiment']
                print(f"{stock['ticker']:<8} ${stock['price']:<9.2f} {tech['rsi']:<8.1f} "
                      f"{tech['macd_trend']:<10} {ml['direction']:<10} {sent['overall_sentiment']:<15}")
            print()
        
        # HOLD signals
        if hold_stocks:
            print(f"{'YELLOW HOLD SIGNALS':^100}")
            print(f"-{'-'*98}-")
            print(f"{'Ticker':<8} {'Price':<10} {'RSI':<8} {'MACD':<10} {'ML':<10}")
            print(f"-{'-'*98}-")
            for stock in hold_stocks[:top_n]:
                tech = stock['technical']
                ml = stock['ml_prediction']
                print(f"{stock['ticker']:<8} ${stock['price']:<9.2f} {tech['rsi']:<8.1f} "
                      f"{tech['macd_trend']:<10} {ml['direction']:<10}")
            print()
        
        # Summary
        print(f"\n{'='*100}")
        print(f"SUMMARY: {len(buy_stocks)} BUY | {len(sell_stocks)} SELL | {len(hold_stocks)} HOLD")
        print(f"{'='*100}\n")


def main():
    """Run the scanner in test mode"""
    scanner = AITradingScanner(test_mode=True)  # Use TEST_TICKERS (10 stocks)
    results = scanner.scan(period="1y")
    scanner.print_results(top_n=15)
    
    # Save results
    if scanner.results:
        df = pd.DataFrame([{
            'ticker': r['ticker'],
            'price': r['price'],
            'signal': r['signal'],
            'tech_score': r['technical']['score'],
            'ml_direction': r['ml_prediction']['direction'],
            'ml_confidence': r['ml_prediction']['confidence'],
            'sentiment': r['sentiment']['overall_sentiment']
        } for r in scanner.results])
        
        df.to_csv('scanner_results.csv', index=False)
        print(f"\nResults saved to: scanner_results.csv")


if __name__ == "__main__":
    main()
