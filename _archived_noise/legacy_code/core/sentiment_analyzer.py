"""Sentiment analysis based on price momentum, volume, and support/resistance."""


class SentimentAnalyzer:
    """Analyzes market sentiment from technical patterns."""
    
    def __init__(self):
        self.sentiment_scores = {}
    
    def calculate_price_momentum_sentiment(self, data, window=20):
        """Analyze sentiment based on price momentum."""
        if len(data) < window:
            return 0, "NEUTRAL"
        
        recent_returns = float(data['Close'].pct_change().tail(window).mean())
        volatility = float(data['Close'].pct_change().tail(window).std())
        
        if recent_returns > volatility * 0.5:
            return 1.0, "VERY_BULLISH"
        elif recent_returns > 0:
            return 0.5, "BULLISH"
        elif recent_returns < -volatility * 0.5:
            return -1.0, "VERY_BEARISH"
        elif recent_returns < 0:
            return -0.5, "BEARISH"
        else:
            return 0, "NEUTRAL"
    
    def calculate_volume_sentiment(self, data, window=20):
        """Analyze sentiment based on volume patterns."""
        if len(data) < window:
            return 0, "NEUTRAL"
        
        recent_data = data.tail(window)
        returns = recent_data['Close'].pct_change()
        volume_change = recent_data['Volume'].pct_change()
        
        bullish_volume = int(((returns > 0) & (volume_change > 0)).sum())
        bearish_volume = int(((returns < 0) & (volume_change > 0)).sum())
        
        total_volume_events = bullish_volume + bearish_volume
        
        if total_volume_events == 0:
            return 0, "NEUTRAL"
        
        bullish_ratio = bullish_volume / total_volume_events
        
        if bullish_ratio > 0.7:
            return 1.0, "VERY_BULLISH"
        elif bullish_ratio > 0.55:
            return 0.5, "BULLISH"
        elif bullish_ratio < 0.3:
            return -1.0, "VERY_BEARISH"
        elif bullish_ratio < 0.45:
            return -0.5, "BEARISH"
        else:
            return 0, "NEUTRAL"
    
    def detect_support_resistance(self, data, window=20):
        """Detect support/resistance levels for sentiment."""
        if len(data) < window:
            return 0, "NEUTRAL"
        
        recent_data = data['Close'].tail(window)
        current_price = float(recent_data.iloc[-1])
        
        resistance = float(recent_data.max())
        support = float(recent_data.min())
        
        range_price = resistance - support
        
        if range_price == 0:
            return 0, "NEUTRAL"
        
        dist_to_support = (current_price - support) / range_price
        dist_to_resistance = (resistance - current_price) / range_price
        
        if dist_to_support < 0.2:
            return 0.8, "BULLISH"
        elif dist_to_resistance < 0.2:
            return -0.8, "BEARISH"
        elif dist_to_support < dist_to_resistance:
            return 0.3, "SLIGHTLY_BULLISH"
        else:
            return -0.3, "SLIGHTLY_BEARISH"
    
    def analyze(self, data):
        """Run all sentiment analyses."""
        momentum_score, momentum_sentiment = self.calculate_price_momentum_sentiment(data)
        volume_score, volume_sentiment = self.calculate_volume_sentiment(data)
        sr_score, sr_sentiment = self.detect_support_resistance(data)
        
        overall_score = (momentum_score + volume_score + sr_score) / 3
        
        if overall_score > 0.6:
            overall_sentiment = "VERY_BULLISH"
        elif overall_score > 0.2:
            overall_sentiment = "BULLISH"
        elif overall_score < -0.6:
            overall_sentiment = "VERY_BEARISH"
        elif overall_score < -0.2:
            overall_sentiment = "BEARISH"
        else:
            overall_sentiment = "NEUTRAL"
        
        return {
            'overall_score': overall_score,
            'overall_sentiment': overall_sentiment,
            'momentum_score': momentum_score,
            'momentum_sentiment': momentum_sentiment,
            'volume_score': volume_score,
            'volume_sentiment': volume_sentiment,
            'sr_score': sr_score,
            'sr_sentiment': sr_sentiment
        }
