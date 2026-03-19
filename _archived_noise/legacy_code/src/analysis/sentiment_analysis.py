"""
# ============================================================================
# SENTIMENT ANALYSIS MODULE
# ============================================================================
# Market sentiment based on technical patterns and volume
# ============================================================================
"""

import pandas as pd
from typing import Tuple, Dict, Optional, Any


# ============================================================================
# SENTIMENT ANALYZER CLASS
# ============================================================================

class SentimentAnalyzer:
    """
    Analyzes market sentiment from technical and volume patterns.
    
    Factors analyzed:
    - Price momentum: Recent returns vs. volatility
    - Volume patterns: Volume expansion with directional moves
    - Support/Resistance: Price position relative to recent levels
    
    Output: Composite sentiment score (bullish to bearish)
    """
    
    def __init__(self):
        """Initialize sentiment analyzer."""
        self.sentiment_scores: Dict[str, Any] = {}
    
    # ========================================================================
    # MOMENTUM SENTIMENT
    # ========================================================================
    
    def _analyze_momentum(
        self,
        data: pd.DataFrame,
        window: int = 20
    ) -> Tuple[float, str]:
        """
        Analyze sentiment based on price momentum.
        
        Args:
            data: OHLCV DataFrame
            window: Number of periods to analyze
            
        Returns:
            Tuple of (sentiment_score, sentiment_label)
            - score: -1.0 (very bearish) to +1.0 (very bullish)
            - label: Sentiment description
        """
        if len(data) < window:
            return 0.0, "NEUTRAL"
        
        try:
            # Calculate recent returns and volatility
            recent_returns = float(data['Close'].pct_change().tail(window).mean())
            volatility = float(data['Close'].pct_change().tail(window).std())
            
            # Normalize returns by volatility
            if volatility > 0:
                momentum_ratio = recent_returns / volatility
            else:
                momentum_ratio = 0
            
            # Score sentiment
            if momentum_ratio > 0.5:
                return 1.0, "VERY_BULLISH"
            elif momentum_ratio > 0.1:
                return 0.5, "BULLISH"
            elif momentum_ratio < -0.5:
                return -1.0, "VERY_BEARISH"
            elif momentum_ratio < -0.1:
                return -0.5, "BEARISH"
            else:
                return 0.0, "NEUTRAL"
                
        except Exception as e:
            print(f"Momentum Error: {e}")
            return 0.0, "UNKNOWN"
    
    # ========================================================================
    # VOLUME SENTIMENT
    # ========================================================================
    
    def _analyze_volume(
        self,
        data: pd.DataFrame,
        window: int = 20
    ) -> Tuple[float, str]:
        """
        Analyze sentiment based on volume patterns.
        
        Bullish volume: Price up on high volume
        Bearish volume: Price down on high volume
        
        Args:
            data: OHLCV DataFrame
            window: Number of periods to analyze
            
        Returns:
            Tuple of (sentiment_score, sentiment_label)
        """
        if len(data) < window:
            return 0.0, "NEUTRAL"
        
        try:
            recent_data = data.tail(window)
            returns = recent_data['Close'].pct_change()
            volume_change = recent_data['Volume'].pct_change()
            
            # Count bullish and bearish volume
            bullish_vol = int(((returns > 0) & (volume_change > 0)).sum())
            bearish_vol = int(((returns < 0) & (volume_change > 0)).sum())
            
            total_events = bullish_vol + bearish_vol
            
            if total_events == 0:
                return 0.0, "NEUTRAL"
            
            bullish_ratio = bullish_vol / total_events
            
            # Score sentiment
            if bullish_ratio > 0.7:
                return 1.0, "VERY_BULLISH"
            elif bullish_ratio > 0.55:
                return 0.5, "BULLISH"
            elif bullish_ratio < 0.3:
                return -1.0, "VERY_BEARISH"
            elif bullish_ratio < 0.45:
                return -0.5, "BEARISH"
            else:
                return 0.0, "NEUTRAL"
                
        except Exception as e:
            print(f"Volume Error: {e}")
            return 0.0, "UNKNOWN"
    
    # ========================================================================
    # SUPPORT/RESISTANCE SENTIMENT
    # ========================================================================
    
    def _analyze_support_resistance(
        self,
        data: pd.DataFrame,
        window: int = 20
    ) -> Tuple[float, str]:
        """
        Analyze sentiment based on support/resistance levels.
        
        Near support = bullish (upside potential)
        Near resistance = bearish (downside risk)
        
        Args:
            data: OHLCV DataFrame
            window: Number of periods to analyze
            
        Returns:
            Tuple of (sentiment_score, sentiment_label)
        """
        if len(data) < window:
            return 0.0, "NEUTRAL"
        
        try:
            recent = data['Close'].tail(window)
            current_price = float(recent.iloc[-1])
            resistance = float(recent.max())
            support = float(recent.min())
            
            price_range = resistance - support
            
            if price_range == 0:
                return 0.0, "NEUTRAL"
            
            # Calculate distance to support/resistance
            dist_to_support = (current_price - support) / price_range
            dist_to_resistance = (resistance - current_price) / price_range
            
            # Score sentiment
            if dist_to_support < 0.2:
                return 0.8, "BULLISH"  # Near support
            elif dist_to_resistance < 0.2:
                return -0.8, "BEARISH"  # Near resistance
            elif dist_to_support < dist_to_resistance:
                return 0.3, "SLIGHTLY_BULLISH"
            else:
                return -0.3, "SLIGHTLY_BEARISH"
                
        except Exception as e:
            print(f"Support/Resistance Error: {e}")
            return 0.0, "UNKNOWN"
    
    # ========================================================================
    # COMPOSITE SENTIMENT
    # ========================================================================
    
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run all sentiment analyses and produce composite sentiment.
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Dictionary with all sentiment components and overall score
        """
        try:
            # Individual sentiment scores
            momentum_score, momentum_label = self._analyze_momentum(data)
            volume_score, volume_label = self._analyze_volume(data)
            sr_score, sr_label = self._analyze_support_resistance(data)
            
            # Composite score (weighted average)
            composite_score = (momentum_score + volume_score + sr_score) / 3.0
            composite_score = max(-1.0, min(1.0, composite_score))
            
            # Overall sentiment label
            if composite_score > 0.6:
                overall_label = "VERY_BULLISH"
            elif composite_score > 0.2:
                overall_label = "BULLISH"
            elif composite_score < -0.6:
                overall_label = "VERY_BEARISH"
            elif composite_score < -0.2:
                overall_label = "BEARISH"
            else:
                overall_label = "NEUTRAL"
            
            self.sentiment_scores = {
                'momentum_score': momentum_score,
                'momentum_sentiment': momentum_label,
                'volume_score': volume_score,
                'volume_sentiment': volume_label,
                'sr_score': sr_score,
                'sr_sentiment': sr_label,
                'overall_score': composite_score,
                'overall_sentiment': overall_label,
            }
            
            return self.sentiment_scores
            
        except Exception as e:
            print(f"Analysis Error: {e}")
            return {
                'momentum_score': 0.0,
                'momentum_sentiment': 'UNKNOWN',
                'volume_score': 0.0,
                'volume_sentiment': 'UNKNOWN',
                'sr_score': 0.0,
                'sr_sentiment': 'UNKNOWN',
                'overall_score': 0.0,
                'overall_sentiment': 'UNKNOWN',
            }
