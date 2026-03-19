"""Technical analysis indicators - RSI, MACD, Moving Averages."""

import pandas as pd
import numpy as np


class TechnicalAnalyzer:
    """Calculates technical indicators and generates signals."""
    
    def __init__(self, data):
        self.data = data.copy()
        self.signals = {}
    
    def calculate_rsi(self, period=14):
        """Calculate Relative Strength Index (14-period)."""
        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        self.signals['RSI'] = rsi.iloc[-1]
        self.signals['RSI_signal'] = (
            'BUY' if rsi.iloc[-1] < 30 
            else 'SELL' if rsi.iloc[-1] > 70 
            else 'NEUTRAL'
        )
        return rsi
    
    def calculate_macd(self, fast=12, slow=26, signal=9):
        """Calculate MACD (Moving Average Convergence Divergence)."""
        ema_fast = self.data['Close'].ewm(span=fast).mean()
        ema_slow = self.data['Close'].ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        histogram = macd - macd_signal
        
        self.signals['MACD'] = macd.iloc[-1]
        self.signals['MACD_signal'] = macd_signal.iloc[-1]
        self.signals['MACD_histogram'] = histogram.iloc[-1]
        self.signals['MACD_trend'] = (
            'BULLISH' if macd.iloc[-1] > macd_signal.iloc[-1] 
            else 'BEARISH'
        )
        
        return macd, macd_signal, histogram
    
    def calculate_moving_averages(self, short=20, long=50):
        """Calculate Simple Moving Averages (20 and 50-period)."""
        sma_short = self.data['Close'].rolling(window=short).mean()
        sma_long = self.data['Close'].rolling(window=long).mean()
        
        current_price = self.data['Close'].iloc[-1]
        sma_short_val = sma_short.iloc[-1]
        sma_long_val = sma_long.iloc[-1]
        
        self.signals['Price'] = current_price
        self.signals['SMA_20'] = sma_short_val
        self.signals['SMA_50'] = sma_long_val
        
        if current_price > sma_short_val > sma_long_val:
            self.signals['MA_trend'] = 'STRONG_UPTREND'
        elif current_price > sma_long_val:
            self.signals['MA_trend'] = 'UPTREND'
        elif current_price < sma_short_val < sma_long_val:
            self.signals['MA_trend'] = 'STRONG_DOWNTREND'
        elif current_price < sma_long_val:
            self.signals['MA_trend'] = 'DOWNTREND'
        else:
            self.signals['MA_trend'] = 'SIDEWAYS'
        
        return sma_short, sma_long
    
    def analyze(self):
        """Run all technical indicators."""
        self.calculate_rsi()
        self.calculate_macd()
        self.calculate_moving_averages()
        return self.signals
    
    def get_score(self):
        """Generate buy/sell score (-5 to +5)."""
        score = 0
        
        if self.signals.get('RSI_signal') == 'BUY':
            score += 2
        elif self.signals.get('RSI_signal') == 'SELL':
            score -= 2
        
        if self.signals.get('MACD_trend') == 'BULLISH':
            score += 2
        elif self.signals.get('MACD_trend') == 'BEARISH':
            score -= 2
        
        ma_trend = self.signals.get('MA_trend')
        if ma_trend == 'STRONG_UPTREND':
            score += 2
        elif ma_trend == 'UPTREND':
            score += 1
        elif ma_trend == 'STRONG_DOWNTREND':
            score -= 2
        elif ma_trend == 'DOWNTREND':
            score -= 1
        
        return max(-5, min(5, score))
