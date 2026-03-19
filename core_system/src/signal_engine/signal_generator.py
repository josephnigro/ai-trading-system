"""
Signal engine - generates trading signals from market data.
Refactored from existing technical_analysis.py, ml_predictor.py, sentiment_analysis.py
"""

import pandas as pd
from typing import Optional, List
from datetime import datetime

from ..core.signal import Signal, SignalType
from ..core.base_module import BaseModule


class AnalysisEngine(BaseModule):
    """Base class for analysis engines."""
    
    def analyze(self, data: pd.DataFrame) -> dict:
        """Run analysis on data. Override in subclasses."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Analysis engines are valid if they can be initialized."""
        return True

    def _to_series(self, values: pd.Series | pd.DataFrame) -> pd.Series:
        """Normalize yfinance output to a 1D series."""
        if isinstance(values, pd.DataFrame):
            if values.shape[1] == 0:
                return pd.Series(dtype=float)
            return values.iloc[:, 0]
        return values


class TechnicalAnalysis(AnalysisEngine):
    """Technical analysis - RSI, MACD, Moving Averages."""
    
    def __init__(self):
        super().__init__("TechnicalAnalysis")
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
    
    def analyze(self, data: pd.DataFrame) -> dict:
        """Run technical analysis."""
        try:
            results = {
                'rsi': self._calculate_rsi(data),
                'macd': self._calculate_macd(data),
                'ma_trend': self._calculate_ma_trend(data),
                'score': 0.0
            }
            
            # Calculate overall score (-5 to +5)
            results['score'] = self._score_technicals(results)
            return results
        
        except Exception as e:
            self.log_error(f"Technical analysis failed: {str(e)}")
            return {'error': str(e), 'score': 0.0}
    
    def _calculate_rsi(self, data: pd.DataFrame) -> float:
        """Calculate RSI indicator."""
        closes = self._to_series(data['Close'])
        delta = closes.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        loss_safe = loss.replace(0, pd.NA)
        rs = gain / loss_safe
        rsi_series = 100 - (100 / (1 + rs))
        latest_rsi = rsi_series.iloc[-1]
        return float(latest_rsi) if not pd.isna(latest_rsi) else 50.0
    
    def _calculate_macd(self, data: pd.DataFrame) -> dict:
        """Calculate MACD."""
        closes = self._to_series(data['Close'])
        ema_fast = closes.ewm(span=self.macd_fast).mean()
        ema_slow = closes.ewm(span=self.macd_slow).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=self.macd_signal).mean()
        histogram = macd_line - macd_signal
        
        return {
            'macd': float(macd_line.iloc[-1]),
            'signal': float(macd_signal.iloc[-1]),
            'histogram': float(histogram.iloc[-1])
        }
    
    def _calculate_ma_trend(self, data: pd.DataFrame) -> dict:
        """Calculate moving average trend."""
        closes = self._to_series(data['Close'])
        ma20 = closes.rolling(window=20).mean()
        ma50 = closes.rolling(window=50).mean()
        
        current_price = closes.iloc[-1]
        current_ma20 = ma20.iloc[-1]
        current_ma50 = ma50.iloc[-1]
        
        uptrend = current_price > current_ma20 > current_ma50
        downtrend = current_price < current_ma20 < current_ma50
        
        return {
            'ma20': float(current_ma20),
            'ma50': float(current_ma50),
            'uptrend': uptrend,
            'downtrend': downtrend
        }
    
    def _score_technicals(self, results: dict) -> float:
        """Score technical setup."""
        score = 0.0
        
        rsi = results['rsi']
        if rsi < 30:
            score += 1.5  # Oversold
        elif rsi > 70:
            score -= 1.5  # Overbought
        
        macd_hist = results['macd']['histogram']
        if macd_hist > 0:
            score += 1.0
        else:
            score -= 1.0
        
        if results['ma_trend']['uptrend']:
            score += 1.5
        elif results['ma_trend']['downtrend']:
            score -= 1.5
        
        return max(-5, min(5, score))  # Clamp to -5 to +5


class MLPredictor(AnalysisEngine):
    """Machine Learning price direction prediction."""
    
    def __init__(self):
        super().__init__("MLPredictor")
    
    def analyze(self, data: pd.DataFrame) -> dict:
        """Run ML analysis."""
        try:
            # Simple momentum-based prediction
            closes = self._to_series(data['Close'])
            returns = closes.pct_change()
            recent_momentum = returns.tail(10).mean()
            volatility = returns.tail(20).std()
            
            # Predict direction
            direction = 'UP' if recent_momentum > 0.001 else ('DOWN' if recent_momentum < -0.001 else 'NEUTRAL')
            
            # Confidence based on momentum vs volatility
            if volatility > 0:
                confidence = min(0.95, abs(recent_momentum) / volatility)
            else:
                confidence = 0.5
            
            # Score: -1 to +1
            score = (confidence if direction == 'UP' else (-confidence if direction == 'DOWN' else 0.0))
            
            return {
                'direction': direction,
                'confidence': confidence,
                'score': score * 2  # Scale to -2 to +2
            }
        
        except Exception as e:
            self.log_error(f"ML analysis failed: {str(e)}")
            return {'direction': 'UNKNOWN', 'confidence': 0.0, 'score': 0.0}


class SentimentAnalysis(AnalysisEngine):
    """Sentiment analysis - volume, momentum, support/resistance."""
    
    def __init__(self):
        super().__init__("SentimentAnalysis")
    
    def analyze(self, data: pd.DataFrame) -> dict:
        """Run sentiment analysis."""
        try:
            closes = self._to_series(data['Close'])
            highs = self._to_series(data['High'])
            lows = self._to_series(data['Low'])
            volumes = self._to_series(data['Volume'])

            # Volume analysis
            recent_volume = volumes.tail(5).mean()
            historical_volume = volumes.tail(50).mean()
            volume_strength = recent_volume / historical_volume if historical_volume > 0 else 1.0
            
            # Momentum analysis
            returns = closes.pct_change()
            bullish_days = (returns.tail(10) > 0).sum()
            bullish_ratio = bullish_days / 10
            
            # Support/resistance
            high_52w = highs.tail(252).max()
            low_52w = lows.tail(252).min()
            current = closes.iloc[-1]
            distance_to_high = (high_52w - current) / high_52w if high_52w > 0 else 0
            
            # Overall sentiment score
            sentiment = 'BULLISH' if bullish_ratio > 0.6 else ('BEARISH' if bullish_ratio < 0.4 else 'NEUTRAL')
            
            # Score: -1 to +1
            score = (bullish_ratio - 0.5) * 2  # Scale to -1 to +1
            if volume_strength > 1.2:
                score += 0.5
            
            return {
                'sentiment': sentiment,
                'bullish_ratio': bullish_ratio,
                'volume_strength': volume_strength,
                'distance_to_52w_high': distance_to_high,
                'score': max(-2, min(2, score * 2))  # Scale and clamp
            }
        
        except Exception as e:
            self.log_error(f"Sentiment analysis failed: {str(e)}")
            return {'sentiment': 'UNKNOWN', 'score': 0.0}


class SignalEngine(BaseModule):
    """
    Main signal engine.
    Combines multiple analysis engines to generate trading signals.
    """
    
    def __init__(self):
        super().__init__("SignalEngine")
        self.technical = TechnicalAnalysis()
        self.ml = MLPredictor()
        self.sentiment = SentimentAnalysis()
        self.signals: List[Signal] = []
        self.last_rejection_reason: str = ""
    
    def initialize(self) -> bool:
        """Initialize all analysis engines."""
        modules = [self.technical, self.ml, self.sentiment]
        for module in modules:
            if not module.initialize():
                self.log_error(f"Failed to initialize {module.name}")
                return False
        return super().initialize()
    
    def generate_signal(
        self,
        ticker: str,
        data: pd.DataFrame,
        current_price: float
    ) -> Optional[Signal]:
        """
        Generate a trading signal for a ticker.
        
        Args:
            ticker: Stock ticker
            data: OHLCV data
            current_price: Current market price
        
        Returns:
            Signal object or None if analysis failed
        """
        try:
            self.last_rejection_reason = ""

            if len(data) < 50:
                self.log_error(f"{ticker}: Insufficient data ({len(data)} rows)")
                self.last_rejection_reason = "insufficient_data"
                return None
            
            # Run all analysis engines
            tech_results = self.technical.analyze(data)
            ml_results = self.ml.analyze(data)
            sentiment_results = self.sentiment.analyze(data)
            
            # Combine scores
            technical_score = tech_results.get('score', 0.0)
            ml_score = ml_results.get('score', 0.0)
            sentiment_score = sentiment_results.get('score', 0.0)
            
            # Average to get 0-100 confidence (transform from -5/+5 scale)
            avg_score = (technical_score + ml_score + sentiment_score) / 3
            confidence = ((avg_score + 5) / 10) * 100  # Transform to 0-100
            
            # Determine signal type
            if avg_score > 1.0:
                signal_type = SignalType.BUY
            elif avg_score < -1.0:
                signal_type = SignalType.SELL
            else:
                ma_trend = tech_results.get("ma_trend", {}) if isinstance(tech_results, dict) else {}
                ma20 = ma_trend.get("ma20") if isinstance(ma_trend, dict) else None
                if ma20 is not None and current_price < ma20:
                    self.last_rejection_reason = "below_ma"
                else:
                    self.last_rejection_reason = "breakout_fail"
                return None  # No clear signal
            
            # Calculate targets
            atr = self._calculate_atr(data)
            entry_price = current_price
            profit_target = entry_price + (atr * 1.5) if signal_type == SignalType.BUY else entry_price - (atr * 1.5)
            stop_loss = entry_price - (atr * 0.5) if signal_type == SignalType.BUY else entry_price + (atr * 0.5)
            
            # Build signal
            signal = Signal(
                ticker=ticker,
                signal_type=signal_type,
                current_price=current_price,
                entry_price=entry_price,
                profit_target=profit_target,
                stop_loss=stop_loss,
                technical_score=technical_score,
                ml_score=ml_score,
                sentiment_score=sentiment_score,
                overall_confidence=confidence,
                reason=f"Tech:{technical_score:.1f} ML:{ml_score:.1f} Sentiment:{sentiment_score:.1f}",
                analysis_data={
                    'technical': tech_results,
                    'ml': ml_results,
                    'sentiment': sentiment_results
                }
            )
            
            self.signals.append(signal)
            return signal
        
        except Exception as e:
            self.log_error(f"Failed to generate signal for {ticker}: {str(e)}")
            self.last_rejection_reason = "signal_generation_error"
            return None
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        high = self.technical._to_series(data['High'])
        low = self.technical._to_series(data['Low'])
        close = self.technical._to_series(data['Close'])
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.1
    
    def validate(self) -> bool:
        """Validate signal engine is working."""
        return all(m.validate() for m in [self.technical, self.ml, self.sentiment])
