# ==============================
# AI TRADING SCANNER
# ==============================

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import pandas as pd
from datetime import datetime
from data_engine import DataEngine
from technical_analysis import TechnicalAnalyzer
from ml_predictor import MLPredictor
from sentiment_analyzer import SentimentAnalyzer


def _configure_console_output():
    """Use UTF-8 console output when the runtime supports reconfiguration."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            continue

class AITradingScanner:
    """
    Complete AI Trading Scanner
    Combines technical analysis, ML predictions, and sentiment analysis
    """
    
    # Small-cap / Penny stocks under $100 (high volatility, swing trade opportunities)
    SP500_TICKERS = [
        # High-volatility symbols that are actively traded
        'GME', 'AMC', 'SOFI', 'PLTR', 'LCID', 'NIO', 'CLOV', 'CLNE',
        'OCGN', 'SPCE', 'NVAX', 'RIOT', 'TLRY', 'SNDL', 'ATER', 'BLNK',
        'FUBO', 'PRPL', 'RIG', 'KODK', 'BNGO', 'IDEX', 'AAL', 'UBER',
        'SNAP', 'PINS', 'HOOD', 'OPEN', 'MARA', 'CHPT'
    ]
    
    def __init__(self, tickers=None):
        _configure_console_output()
        if tickers is None:
            tickers = self.SP500_TICKERS
        
        self.tickers = tickers
        self.results = []
        self.data_engine = DataEngine(tickers)
        self.scan_timestamp = None
    
    def scan(self, period="1y"):
        """
        Run complete scan on all tickers
        """
        print(f"\n{'='*80}")
        print(f"AI TRADING SCANNER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        self.scan_timestamp = datetime.now()
        
        # Fetch data
        print("Step 1: Fetching market data...")
        market_data = self.data_engine.fetch_data(period=period, interval="1d")
        print(f"✓ Data fetched for {len(market_data)} stocks\n")
        
        # Analyze each stock
        print("Step 2: Analyzing stocks...")
        for ticker in self.tickers:
            if ticker not in market_data:
                continue
            
            try:
                print(f"  → Analyzing {ticker}...", end=" ")
                analysis = self.analyze_stock(ticker, market_data[ticker])
                self.results.append(analysis)
                print("✓")
            except Exception as e:
                print(f"✗ Error: {e}")
        
        print(f"\n✓ Analysis complete for {len(self.results)} stocks\n")
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
        
        # Generate signal - reduced thresholds for more signals
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
        print(f"SCAN RESULTS - {self.scan_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}\n")
        
        # BUY signals
        if buy_stocks:
            print(f"{'GREEN BUY SIGNALS':^100}")
            print(f"-{'─'*98}-")
            print(f"{'Ticker':<8} {'Price':<10} {'RSI':<8} {'MACD':<10} {'ML':<10} {'Sentiment':<15} {'Score':<10}")
            print(f"-{'─'*98}-")
            for stock in buy_stocks[:top_n]:
                tech = stock['technical']
                ml = stock['ml_prediction']
                sent = stock['sentiment']
                print(f"{stock['ticker']:<8} ${stock['price']:<9.2f} {tech['rsi']:<8.1f} "
                      f"{tech['macd_trend']:<10} {ml['direction']:<10} {sent['overall_sentiment']:<15} "
                      f"{'+'+str(int(stock['price']))}")
            print()
        
        # SELL signals
        if sell_stocks:
            print(f"{'RED SELL SIGNALS':^100}")
            print(f"-{'─'*98}-")
            print(f"{'Ticker':<8} {'Price':<10} {'RSI':<8} {'MACD':<10} {'ML':<10} {'Sentiment':<15} {'Score':<10}")
            print(f"-{'─'*98}-")
            for stock in sell_stocks[:top_n]:
                tech = stock['technical']
                ml = stock['ml_prediction']
                sent = stock['sentiment']
                print(f"{stock['ticker']:<8} ${stock['price']:<9.2f} {tech['rsi']:<8.1f} "
                      f"{tech['macd_trend']:<10} {ml['direction']:<10} {sent['overall_sentiment']:<15} "
                      f"{'-'+str(int(stock['price']))}")
            print()
        
        # Summary statistics
        print(f"{'='*100}")
        print(f"SUMMARY: {len(buy_stocks)} BUY | {len(sell_stocks)} SELL | {len(hold_stocks)} HOLD")
        print(f"{'='*100}\n")
    
    def export_to_csv(self, filename='scanner_results.csv'):
        """
        Export results to CSV
        """
        if not self.results:
            print("No results to export.")
            return
        
        records = []
        for stock in self.results:
            record = {
                'Ticker': stock['ticker'],
                'Price': stock['price'],
                'Date': stock['date'],
                'Signal': stock['signal'],
                'RSI': stock['technical']['rsi'],
                'MACD_Trend': stock['technical']['macd_trend'],
                'MA_Trend': stock['technical']['ma_trend'],
                'Tech_Score': stock['technical']['score'],
                'ML_Direction': stock['ml_prediction']['direction'],
                'ML_Confidence': stock['ml_prediction']['confidence'],
                'ML_Predicted_Change_Pct': stock['ml_prediction']['predicted_change_pct'],
                'Sentiment': stock['sentiment']['overall_sentiment'],
                'Sentiment_Score': stock['sentiment']['overall_score']
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        df.to_csv(filename, index=False)
        print(f"✓ Results exported to {filename}")

if __name__ == "__main__":
    scanner = AITradingScanner()
    results = scanner.scan(period="1y")
    scanner.print_results(top_n=10)
    scanner.export_to_csv()