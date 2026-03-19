"""Filters weak signals and validates trade quality."""


class SignalFilter:
    """Filters out weak, unreliable signals."""
    
    def __init__(self):
        self.filter_config = {
            'min_price': 2.0,
            'min_volume_dollars': 500000,
            'min_rsi': 10,
            'max_rsi': 90,
            'min_ml_confidence': 0.2,
            'min_sentiment_score': -0.7,
        }
    
    def filter_signal(self, stock_data, signal):
        """Apply filters to a signal."""
        reasons = []
        passes = True
        
        if stock_data['price'] < self.filter_config['min_price']:
            reasons.append(f"Price too low: ${stock_data['price']:.2f}")
            passes = False
        
        if 'volume_dollars' in stock_data:
            if stock_data['volume_dollars'] < self.filter_config['min_volume_dollars']:
                reasons.append(f"Volume too low: ${stock_data['volume_dollars']:,.0f}")
                passes = False
        
        if 'technical' in signal:
            rsi = signal['technical'].get('rsi', 50)
            if rsi < self.filter_config['min_rsi']:
                reasons.append(f"RSI too low: {rsi:.1f}")
                passes = False
            if rsi > self.filter_config['max_rsi']:
                reasons.append(f"RSI too high: {rsi:.1f}")
                passes = False
        
        if 'ml_prediction' in signal:
            ml_confidence = signal['ml_prediction'].get('confidence', 0)
            if ml_confidence < self.filter_config['min_ml_confidence']:
                reasons.append(f"ML confidence too low: {ml_confidence:.2f}")
        
        if 'sentiment' in signal:
            sentiment_score = signal['sentiment'].get('overall_score', 0)
            if signal.get('signal') == 'BUY' and sentiment_score < self.filter_config['min_sentiment_score']:
                reasons.append(f"Sentiment bearish: {sentiment_score:.2f}")
        
        return passes, reasons
    
    def filter_signals(self, results):
        """Filter multiple signals."""
        filtered = []
        filtered_out = {}
        
        for stock in results:
            ticker = stock['ticker']
            stock_data = {
                'price': stock.get('price', 0),
                'volume_dollars': stock.get('volume_dollars', 0),
            }
            
            passes, reasons = self.filter_signal(stock_data, stock)
            
            if passes:
                filtered.append(stock)
            else:
                filtered_out[ticker] = reasons
        
        print(f"\n📊 SIGNAL FILTERING RESULTS:")
        print(f"  ✓ Quality signals: {len(filtered)}")
        print(f"  ✗ Filtered out: {len(filtered_out)}")
        
        return filtered, filtered_out
    
    def get_filter_status(self):
        """Return current filter configuration."""
        return {
            'min_price': f"${self.filter_config['min_price']:.2f}",
            'min_volume_dollars': f"${self.filter_config['min_volume_dollars']:,.0f}",
            'rsi_range': f"{self.filter_config['min_rsi']:.0f} - {self.filter_config['max_rsi']:.0f}",
            'min_ml_confidence': f"{self.filter_config['min_ml_confidence']:.2f}",
        }
