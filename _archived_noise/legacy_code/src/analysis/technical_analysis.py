"""
# ============================================================================
# TECHNICAL ANALYSIS MODULE
# ============================================================================
# Computes RSI, MACD, Moving Averages and generates trading signals
# ============================================================================
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Any


# ============================================================================
# CONFIGURATION
# ============================================================================

RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

MA_SHORT = 20
MA_LONG = 50


# ============================================================================
# TECHNICAL ANALYZER CLASS
# ============================================================================

class TechnicalAnalyzer:
    """
    Calculates technical indicators from OHLCV price data.
    
    Indicators:
    - RSI (14-period): Momentum and overbought/oversold
    - MACD: Trend direction and momentum
    - Moving Averages (20, 50): Support/resistance and trend
    
    Output: Dictionary of signals for use in trading decisions
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize with OHLCV DataFrame.
        
        Args:
            data: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self.signals: Dict[str, Any] = {}
    
    # ========================================================================
    # RSI INDICATOR
    # ========================================================================
    
    def calculate_rsi(self, period: int = RSI_PERIOD) -> Optional[pd.Series]:
        """
        Calculate Relative Strength Index (momentum indicator).
        
        Args:
            period: RSI period (default 14)
            
        Returns:
            Series of RSI values
        """
        try:
            delta = self.data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            # Avoid division by zero
            rs = gain / loss.replace(0, 1e-10)
            rsi = 100 - (100 / (1 + rs))
            
            current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
            
            # Generate signal
            if current_rsi < RSI_OVERSOLD:
                signal = 'OVERSOLD'
            elif current_rsi > RSI_OVERBOUGHT:
                signal = 'OVERBOUGHT'
            else:
                signal = 'NEUTRAL'
            
            self.signals['RSI'] = current_rsi
            self.signals['RSI_signal'] = signal
            
            return rsi
            
        except Exception as e:
            print(f"RSI Error: {e}")
            return None
    
    # ========================================================================
    # MACD INDICATOR
    # ========================================================================
    
    def calculate_macd(
        self,
        fast: int = MACD_FAST,
        slow: int = MACD_SLOW,
        signal: int = MACD_SIGNAL
    ) -> Optional[tuple]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)
            
        Returns:
            Tuple of (macd, signal_line, histogram)
        """
        try:
            ema_fast = self.data['Close'].ewm(span=fast, adjust=False).mean()
            ema_slow = self.data['Close'].ewm(span=slow, adjust=False).mean()
            macd = ema_fast - ema_slow
            macd_signal = macd.ewm(span=signal, adjust=False).mean()
            histogram = macd - macd_signal
            
            current_macd = float(macd.iloc[-1])
            current_signal = float(macd_signal.iloc[-1])
            current_histogram = float(histogram.iloc[-1])
            
            # Generate signal
            trend = 'BULLISH' if current_macd > current_signal else 'BEARISH'
            
            self.signals['MACD'] = current_macd
            self.signals['MACD_signal'] = current_signal
            self.signals['MACD_histogram'] = current_histogram
            self.signals['MACD_trend'] = trend
            
            return macd, macd_signal, histogram
            
        except Exception as e:
            print(f"MACD Error: {e}")
            return None
    
    # ========================================================================
    # MOVING AVERAGES
    # ========================================================================
    
    def calculate_moving_averages(
        self,
        short: int = MA_SHORT,
        long: int = MA_LONG
    ) -> Optional[tuple]:
        """
        Calculate Simple Moving Averages.
        
        Args:
            short: Short MA period (default 20)
            long: Long MA period (default 50)
            
        Returns:
            Tuple of (ma_short, ma_long)
        """
        try:
            ma_short = self.data['Close'].rolling(window=short).mean()
            ma_long = self.data['Close'].rolling(window=long).mean()
            
            current_price = float(self.data['Close'].iloc[-1])
            current_ma_short = float(ma_short.iloc[-1])
            current_ma_long = float(ma_long.iloc[-1])
            
            # Generate signal based on moving average relationship
            if current_price > current_ma_short > current_ma_long:
                trend = 'STRONG_UPTREND'
            elif current_price > current_ma_long:
                trend = 'UPTREND'
            elif current_price < current_ma_short < current_ma_long:
                trend = 'STRONG_DOWNTREND'
            elif current_price < current_ma_long:
                trend = 'DOWNTREND'
            else:
                trend = 'SIDEWAYS'
            
            self.signals['Price'] = current_price
            self.signals['MA_short'] = current_ma_short
            self.signals['MA_long'] = current_ma_long
            self.signals['MA_trend'] = trend
            
            return ma_short, ma_long
            
        except Exception as e:
            print(f"MA Error: {e}")
            return None
    
    # ========================================================================
    # ANALYSIS & SCORING
    # ========================================================================
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run all technical indicators.
        
        Returns:
            Dictionary of all signals
        """
        self.calculate_rsi()
        self.calculate_macd()
        self.calculate_moving_averages()
        return self.signals
    
    def get_score(self, max_score: int = 5) -> float:
        """
        Generate composite buy/sell score (-5 to +5).
        
        Args:
            max_score: Maximum score magnitude (default 5)
            
        Returns:
            Score from -max_score to +max_score
        """
        score = 0.0
        
        # RSI contribution
        if self.signals.get('RSI_signal') == 'OVERSOLD':
            score += 2.0
        elif self.signals.get('RSI_signal') == 'OVERBOUGHT':
            score -= 2.0
        
        # MACD contribution
        if self.signals.get('MACD_trend') == 'BULLISH':
            score += 2.0
        elif self.signals.get('MACD_trend') == 'BEARISH':
            score -= 2.0
        
        # Moving Average contribution
        ma_trend = self.signals.get('MA_trend')
        if ma_trend == 'STRONG_UPTREND':
            score += 2.0
        elif ma_trend == 'UPTREND':
            score += 1.0
        elif ma_trend == 'STRONG_DOWNTREND':
            score -= 2.0
        elif ma_trend == 'DOWNTREND':
            score -= 1.0
        
        # Clamp to valid range
        return max(-max_score, min(max_score, score))
