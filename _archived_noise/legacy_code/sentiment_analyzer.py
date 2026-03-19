# ==============================
# SENTIMENT ANALYZER MODULE
# ==============================

from datetime import datetime, timedelta

class SentimentAnalyzer:
    """
    Sentiment analysis for stocks
    Uses simple heuristics and news-based analysis
    """
    
    def __init__(self):
        self.sentiment_scores = {}
    
    def calculate_price_momentum_sentiment(self, data, window=20):
        """
        Analyze sentiment based on price momentum
        """
        if len(data) < window:
            return 0, "NEUTRAL"
        
        recent_returns = float(data['Close'].pct_change().tail(window).mean())
        volatility = float(data['Close'].pct_change().tail(window).std())
        
        # Sentiment score: -1 (Very Bearish) to +1 (Very Bullish)
        if recent_returns > volatility * 0.5:
            sentiment_score = 1.0
            sentiment = "VERY_BULLISH"
        elif recent_returns > 0:
            sentiment_score = 0.5
            sentiment = "BULLISH"
        elif recent_returns < -volatility * 0.5:
            sentiment_score = -1.0
            sentiment = "VERY_BEARISH"
        elif recent_returns < 0:
            sentiment_score = -0.5
            sentiment = "BEARISH"
        else:
            sentiment_score = 0
            sentiment = "NEUTRAL"
        
        self.sentiment_scores['momentum'] = sentiment_score
        return sentiment_score, sentiment
    
    def calculate_volume_sentiment(self, data, window=20):
        """
        Analyze sentiment based on volume
        High volume on up days = Bullish
        High volume on down days = Bearish
        """
        if len(data) < window:
            return 0, "NEUTRAL"
        
        recent_data = data.tail(window)
        
        # Calculate returns and volume changes
        returns = recent_data['Close'].pct_change()
        volume_change = recent_data['Volume'].pct_change()
        
        # Count bullish vs bearish volume - use .sum() to get integer count
        bullish_volume = int(((returns > 0) & (volume_change > 0)).sum())
        bearish_volume = int(((returns < 0) & (volume_change > 0)).sum())
        
        total_volume_events = bullish_volume + bearish_volume
        
        if total_volume_events == 0:
            return 0, "NEUTRAL"
        
        # Sentiment based on volume distribution
        bullish_ratio = bullish_volume / total_volume_events
        
        if bullish_ratio > 0.7:
            sentiment_score = 1.0
            sentiment = "VERY_BULLISH"
        elif bullish_ratio > 0.55:
            sentiment_score = 0.5
            sentiment = "BULLISH"
        elif bullish_ratio < 0.3:
            sentiment_score = -1.0
            sentiment = "VERY_BEARISH"
        elif bullish_ratio < 0.45:
            sentiment_score = -0.5
            sentiment = "BEARISH"
        else:
            sentiment_score = 0
            sentiment = "NEUTRAL"
        
        self.sentiment_scores['volume'] = sentiment_score
        return sentiment_score, sentiment
    
    def detect_support_resistance(self, data, window=20):
        """
        Detect support/resistance levels
        Price near resistance = Bearish
        Price near support = Bullish
        """
        if len(data) < window:
            return 0, "NEUTRAL"
        
        recent_data = data['Close'].tail(window)
        current_price = float(recent_data.iloc[-1])
        
        resistance = float(recent_data.max())
        support = float(recent_data.min())
        
        range_price = resistance - support
        
        # Distance to resistance/support as % of range
        dist_to_resistance = (resistance - current_price) / range_price if range_price > 0 else 0.5
        dist_to_support = (current_price - support) / range_price if range_price > 0 else 0.5
        
        # If price is closer to resistance, it's bearish
        # If price is closer to support, it's bullish
        if dist_to_support < 0.2:  # Near support
            sentiment_score = 0.8
            sentiment = "BULLISH"
        elif dist_to_resistance < 0.2:  # Near resistance
            sentiment_score = -0.8
            sentiment = "BEARISH"
        elif dist_to_support < dist_to_resistance:
            sentiment_score = 0.3
            sentiment = "SLIGHTLY_BULLISH"
        else:
            sentiment_score = -0.3
            sentiment = "SLIGHTLY_BEARISH"
        
        self.sentiment_scores['support_resistance'] = sentiment_score
        return sentiment_score, sentiment
    
    def analyze(self, data):
        """
        Run all sentiment analyses
        """
        momentum_score, momentum_sentiment = self.calculate_price_momentum_sentiment(data)
        volume_score, volume_sentiment = self.calculate_volume_sentiment(data)
        sr_score, sr_sentiment = self.detect_support_resistance(data)
        
        # Calculate overall sentiment
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
