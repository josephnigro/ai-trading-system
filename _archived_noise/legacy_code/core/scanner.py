"""Unified stock scanner with AI and momentum analysis modes."""

import sys
import pandas as pd
from datetime import datetime
from .data_engine import DataEngine
from .technical_analysis import TechnicalAnalyzer
from .ml_predictor import MLPredictor
from .sentiment_analyzer import SentimentAnalyzer


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


# Default stock lists
DEFAULT_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'BRK.B', 'JNJ', 'V',
    'WMT', 'JPM', 'PG', 'MA', 'HD', 'DIS', 'PYPL', 'COST', 'NFLX', 'CSCO',
    'PEP', 'ADBE', 'CMCSA', 'INTC', 'AMGN'
]


class Scanner:
    """Unified scanner supporting both AI and momentum analysis modes."""
    
    def __init__(self, tickers=None):
        _configure_console_output()
        self.tickers = tickers if tickers else DEFAULT_TICKERS
        self.results = []
        self.data_engine = DataEngine(self.tickers)
        self.scan_timestamp = None
    
    def scan(self, period="1y", mode="ai"):
        """Run scan in specified mode (ai or momentum)."""
        print(f"\n{'='*80}")
        print(f"SCANNER - {mode.upper()} MODE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        self.scan_timestamp = datetime.now()
        
        print("Step 1: Fetching market data...")
        market_data = self.data_engine.fetch_data(period=period, interval="1d")
        print(f"✓ Data fetched for {len(market_data)} stocks\n")
        
        print("Step 2: Analyzing stocks...")
        for ticker in self.tickers:
            if ticker not in market_data:
                continue
            
            try:
                print(f"  → Analyzing {ticker}...", end=" ")
                
                if mode == "ai":
                    analysis = self._analyze_ai(ticker, market_data[ticker])
                elif mode == "momentum":
                    analysis = self._analyze_momentum(ticker, market_data[ticker])
                else:
                    raise ValueError(f"Unknown mode: {mode}")
                
                if analysis:
                    self.results.append(analysis)
                print("✓")
            except Exception as e:
                print(f"✗ Error: {e}")
        
        print(f"\n✓ Analysis complete for {len(self.results)} stocks\n")
        return self.results
    
    def _analyze_ai(self, ticker, data):
        """AI mode: Technical + ML + Sentiment analysis."""
        analysis = {
            'ticker': ticker,
            'timestamp': self.scan_timestamp,
            'price': data['Close'].iloc[-1],
            'date': data.index[-1],
            'mode': 'ai'
        }
        
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
        
        sentiment_analyzer = SentimentAnalyzer()
        sentiment = sentiment_analyzer.analyze(data)
        
        analysis['sentiment'] = {
            'overall_score': sentiment['overall_score'],
            'overall_sentiment': sentiment['overall_sentiment'],
            'momentum_sentiment': sentiment['momentum_sentiment'],
            'volume_sentiment': sentiment['volume_sentiment']
        }
        
        analysis['signal'] = self._generate_ai_signal(analysis)
        return analysis
    
    def _analyze_momentum(self, ticker, data):
        """Momentum mode: Focus on breakouts and upside potential."""
        if len(data) < 50:
            return None
        
        current_price = float(data['Close'].iloc[-1])
        recent_return = float((data['Close'].iloc[-1] / data['Close'].iloc[-20] - 1) * 100)
        
        ma50 = float(data['Close'].rolling(50).mean().iloc[-1])
        ma200 = float(data['Close'].rolling(200).mean().iloc[-1])
        
        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        
        # Volume
        vol_20 = float(data['Volume'].tail(20).mean())
        vol_50 = float(data['Volume'].tail(50).mean())
        vol_expansion = float((vol_20 / vol_50 - 1) * 100)
        
        # 52-week
        high_52 = float(data['High'].tail(252).max())
        low_52 = float(data['Low'].tail(252).min())
        from_high = float((current_price / high_52 - 1) * 100)
        from_low = float((current_price / low_52 - 1) * 100)
        
        # Calculate upside
        upside_potential = 0
        
        if from_high > -5:
            upside_potential += 15
        elif from_high > -15:
            upside_potential += 10
        
        if current_price > ma50 and ma50 > ma200:
            upside_potential += 10
        
        if vol_expansion > 10:
            upside_potential += 10
        
        if recent_return > 5:
            upside_potential += 10
        elif recent_return > 0:
            upside_potential += 5
        
        if rsi < 70:
            upside_potential += 5
        
        if upside_potential < 15:
            return None
        
        return {
            'ticker': ticker,
            'timestamp': self.scan_timestamp,
            'price': current_price,
            'date': data.index[-1],
            'mode': 'momentum',
            'upside_potential': upside_potential,
            'recent_return': recent_return,
            'rsi': rsi,
            'volume_expansion': vol_expansion,
            'ma50': ma50,
            'ma200': ma200,
            'from_high': from_high,
            'from_low': from_low,
            'high_52': high_52,
            'low_52': low_52
        }
    
    def _generate_ai_signal(self, analysis):
        """Generate BUY/SELL/HOLD signal for AI mode."""
        tech_score = analysis['technical']['score']
        ml_direction = analysis['ml_prediction']['direction']
        sentiment_score = analysis['sentiment']['overall_score']
        
        buy_score = 0
        
        if tech_score > 0:
            buy_score += (tech_score / 5) * 0.4
        
        ml_weight = analysis['ml_prediction']['confidence'] * 0.4
        if ml_direction == 'UP':
            buy_score += ml_weight
        elif ml_direction == 'DOWN':
            buy_score -= ml_weight
        
        if sentiment_score > 0:
            buy_score += (sentiment_score / 1.0) * 0.2
        
        # AGGRESSIVE: Lower thresholds to find more opportunities
        if buy_score > 0.05:  # LOWERED from 0.15
            return 'BUY'
        elif buy_score < -0.05:  # LOWERED from -0.15
            return 'SELL'
        else:
            return 'HOLD'
    
    def print_results(self, top_n=10):
        """Print scan results."""
        if not self.results:
            print("No results to display.")
            return
        
        mode = self.results[0].get('mode', 'ai') if self.results else 'ai'
        
        print(f"\n{'='*100}")
        if self.scan_timestamp:
            print(f"SCAN RESULTS - {self.scan_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"SCAN RESULTS")
        print(f"{'='*100}\n")
        
        if mode == "ai":
            self._print_ai_results(top_n)
        elif mode == "momentum":
            self._print_momentum_results(top_n)
    
    def _print_ai_results(self, top_n=10):
        """Print AI mode results."""
        buy_stocks = [r for r in self.results if r.get('signal') == 'BUY']
        sell_stocks = [r for r in self.results if r.get('signal') == 'SELL']
        hold_stocks = [r for r in self.results if r.get('signal') == 'HOLD']
        
        if buy_stocks:
            print(f"{'GREEN BUY SIGNALS':^100}")
            print("-" * 100)
            print(f"{'Ticker':<8} {'Price':<10} {'RSI':<8} {'MACD':<10} {'ML':<10} {'Sentiment':<15}")
            print("-" * 100)
            for stock in buy_stocks[:top_n]:
                print(f"{stock['ticker']:<8} ${stock['price']:<9.2f} "
                      f"{stock['technical']['rsi']:<8.1f} "
                      f"{stock['technical']['macd_trend']:<10} "
                      f"{stock['ml_prediction']['direction']:<10} "
                      f"{stock['sentiment']['overall_sentiment']:<15}")
            print()
        
        if sell_stocks:
            print(f"{'RED SELL SIGNALS':^100}")
            print("-" * 100)
            print(f"{'Ticker':<8} {'Price':<10} {'RSI':<8} {'MACD':<10} {'ML':<10} {'Sentiment':<15}")
            print("-" * 100)
            for stock in sell_stocks[:top_n]:
                print(f"{stock['ticker']:<8} ${stock['price']:<9.2f} "
                      f"{stock['technical']['rsi']:<8.1f} "
                      f"{stock['technical']['macd_trend']:<10} "
                      f"{stock['ml_prediction']['direction']:<10} "
                      f"{stock['sentiment']['overall_sentiment']:<15}")
            print()
        
        print(f"{'='*100}")
        print(f"SUMMARY: {len(buy_stocks)} BUY | {len(sell_stocks)} SELL | {len(hold_stocks)} HOLD")
        print(f"{'='*100}\n")
    
    def _print_momentum_results(self, top_n=10):
        """Print momentum mode results."""
        by_potential = sorted(self.results, key=lambda x: x['upside_potential'], reverse=True)
        
        print(f"{'Ticker':<8} {'Price':<10} {'Upside':<10} {'Recent %':<12} {'RSI':<8} {'Vol Exp %':<12} {'From High':<12}")
        print("-" * 100)
        
        for stock in by_potential[:top_n]:
            print(f"{stock['ticker']:<8} ${stock['price']:<9.2f} "
                  f"{stock['upside_potential']:<10.0f} "
                  f"{stock['recent_return']:<11.1f}% "
                  f"{stock['rsi']:<7.1f} "
                  f"{stock['volume_expansion']:<11.1f}% "
                  f"{stock['from_high']:<11.1f}%")
        
        print(f"\n{'='*100}")
        print(f"FOUND: {len(self.results)} momentum opportunities")
        print(f"{'='*100}\n")
    
    def export_to_csv(self, filename='scanner_results.csv'):
        """Export results to CSV."""
        if not self.results:
            print("No results to export.")
            return
        
        records = []
        mode = self.results[0].get('mode', 'ai')
        
        for stock in self.results:
            if mode == 'ai':
                record = {
                    'Ticker': stock['ticker'],
                    'Price': stock['price'],
                    'Signal': stock.get('signal', 'UNKNOWN'),
                    'RSI': stock['technical']['rsi'],
                    'MACD_Trend': stock['technical']['macd_trend'],
                    'MA_Trend': stock['technical']['ma_trend'],
                    'ML_Direction': stock['ml_prediction']['direction'],
                    'ML_Confidence': stock['ml_prediction']['confidence'],
                    'Sentiment': stock['sentiment']['overall_sentiment'],
                }
            else:  # momentum
                record = {
                    'Ticker': stock['ticker'],
                    'Price': stock['price'],
                    'Upside_Potential': stock['upside_potential'],
                    'Recent_Return': stock['recent_return'],
                    'RSI': stock['rsi'],
                    'Volume_Expansion': stock['volume_expansion'],
                    'From_52Week_High': stock['from_high'],
                }
            
            records.append(record)
        
        df = pd.DataFrame(records)
        df.to_csv(filename, index=False)
        print(f"✓ Results exported to {filename}")
