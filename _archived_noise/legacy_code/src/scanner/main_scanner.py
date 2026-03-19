"""
# ============================================================================
# MAIN TRADING SCANNER
# ============================================================================
# Unified scanner combining data, analysis, and signal generation
# ============================================================================
"""

from datetime import datetime
from typing import List, Dict, Optional

from ..data import DataEngine
from ..analysis import TechnicalAnalyzer, MLPredictor, SentimentAnalyzer


# ============================================================================
# PENNY STOCK LIST
# ============================================================================

PENNY_STOCKS = [
    'GME', 'AMC', 'BBBY', 'RIDE', 'SOFI', 'PLTR', 'LCID', 'NIO',
    'WISH', 'CLOV', 'CLNE', 'OCGN', 'SPCE', 'NVAX', 'RIOT', 'TLRY',
    'SNDL', 'PROG', 'ATER', 'GNUS', 'CIDM', 'BLNK', 'FUBO', 'PRPL',
    'RIG', 'UXIN', 'KODK', 'BNGO', 'IDEX', 'VROOM'
]


# ============================================================================
# SCANNER CLASS
# ============================================================================

class TradingScanner:
    """
    Unified trading scanner combining multiple analysis methods.
    
    Workflow:
    1. Fetch data from Alpha Vantage
    2. Run technical analysis
    3. Run ML prediction
    4. Analyze sentiment
    5. Generate signals
    """
    
    def __init__(self, tickers: Optional[List[str]] = None, api_key: Optional[str] = None):
        """
        Initialize scanner.
        
        Args:
            tickers: List of stocks to scan (defaults to PENNY_STOCKS)
            api_key: Alpha Vantage API key
        """
        self.tickers = tickers or PENNY_STOCKS
        self.data_engine = DataEngine(self.tickers, api_key=api_key)
        self.results: List[Dict] = []
        self.scan_timestamp: Optional[datetime] = None
    
    def scan(self, period: str = "1y") -> List[Dict]:
        """
        Run complete scan on all tickers.
        
        Args:
            period: Time period ('1w', '1mo', '3mo', '6mo', '1y', '2y')
            
        Returns:
            List of signal dictionaries
        """
        print("\n" + "="*80)
        print(f"TRADING SCANNER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        self.scan_timestamp = datetime.now()
        self.results = []
        
        # Step 1: Fetch data
        print("Step 1: Fetching data...")
        market_data = self.data_engine.fetch_data(period=period)
        print(f"✓ Data ready for {len(market_data)} stocks\n")
        
        # Step 2: Analyze each stock
        print("Step 2: Analyzing stocks...")
        for ticker in self.tickers:
            if ticker not in market_data:
                continue
            
            try:
                print(f"  {ticker}...", end=" ", flush=True)
                analysis = self._analyze_stock(ticker, market_data[ticker])
                if analysis:
                    self.results.append(analysis)
                print("✓")
            except Exception as e:
                print(f"✗ ({e})")
        
        print(f"\n✓ Scan complete: {len(self.results)} signals generated\n")
        return self.results
    
    def _analyze_stock(self, ticker: str, data) -> Optional[Dict]:
        """
        Analyze single stock with all methods.
        
        Returns:
            Signal dictionary or None
        """
        try:
            result = {
                'ticker': ticker,
                'timestamp': self.scan_timestamp,
                'price': float(data['Close'].iloc[-1]),
                'date': data.index[-1]
            }
            
            # Technical analysis
            tech = TechnicalAnalyzer(data)
            tech_signals = tech.analyze()
            tech_score = tech.get_score()
            result['technical_score'] = tech_score
            result['rsi'] = tech_signals.get('RSI', 0)
            result['macd_trend'] = tech_signals.get('MACD_trend', 'UNKNOWN')
            result['ma_trend'] = tech_signals.get('MA_trend', 'UNKNOWN')
            
            # ML prediction
            ml = MLPredictor(data)
            if ml.train(lookback_days=20):
                direction, confidence = ml.predict_direction()
                result['ml_direction'] = direction
                result['ml_confidence'] = confidence
            else:
                result['ml_direction'] = 'UNKNOWN'
                result['ml_confidence'] = 0.0
            
            # Sentiment
            sentiment_obj = SentimentAnalyzer()
            sentiment = sentiment_obj.analyze(data)
            result['sentiment'] = sentiment.get('overall_sentiment', 'UNKNOWN')
            
            # Generate signal
            result['signal'] = self._generate_signal(result)
            result['score'] = self._calculate_score(result)
            
            return result
            
        except Exception as e:
            return None
    
    def _generate_signal(self, analysis: Dict) -> str:
        """Generate BUY/SELL/HOLD signal."""
        tech_score = analysis.get('technical_score', 0)
        ml_dir = analysis.get('ml_direction', 'NEUTRAL')
        
        buy_score = tech_score * 0.5
        if ml_dir == 'UP':
            buy_score += 2.0
        elif ml_dir == 'DOWN':
            buy_score -= 2.0
        
        if buy_score > 1.0:
            return 'BUY'
        elif buy_score < -1.0:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _calculate_score(self, analysis: Dict) -> float:
        """Calculate composite score."""
        score = 0.0
        score += analysis.get('technical_score', 0) * 0.5
        score += (1.0 if analysis.get('ml_direction') == 'UP' else -1.0 if analysis.get('ml_direction') == 'DOWN' else 0.0) * 0.3
        return score
    
    def print_results(self, top_n: int = 15) -> None:
        """Print scan results."""
        if not self.results:
            print("No signals generated")
            return
        
        # Sort by signal type and score
        buy_signals = sorted(
            [r for r in self.results if r.get('signal') == 'BUY'],
            key=lambda x: x.get('score', 0),
            reverse=True
        )
        
        print("\n" + "="*100)
        timestamp_str = self.scan_timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.scan_timestamp else 'UNKNOWN'
        print(f"SCAN RESULTS - {timestamp_str}")
        print("="*100)
        
        if buy_signals:
            print(f"\n{'GREEN BUY SIGNALS':^100}")
            print("-"*100)
            print(f"{'Ticker':<8} {'Price':>10} {'RSI':>8} {'MACD':>12} {'ML':>12} {'Sentiment':>15}")
            print("-"*100)
            
            for stock in buy_signals[:top_n]:
                print(f"{stock['ticker']:<8} ${stock['price']:>9.2f} "
                      f"{stock.get('rsi', 0):>8.1f} "
                      f"{stock.get('macd_trend', 'N/A'):>12} "
                      f"{stock.get('ml_direction', 'N/A'):>12} "
                      f"{stock.get('sentiment', 'N/A'):>15}")
        
        print(f"\n{'='*100}")
        print(f"SUMMARY: {len(buy_signals)} BUY | {len([r for r in self.results if r.get('signal') == 'HOLD'])} HOLD | "
              f"{len([r for r in self.results if r.get('signal') == 'SELL'])} SELL")
        print(f"{'='*100}\n")
