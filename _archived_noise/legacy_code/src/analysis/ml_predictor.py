"""
# ============================================================================
# ML PREDICTOR MODULE
# ============================================================================
# Machine Learning price direction prediction using linear regression
# ============================================================================
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, Optional


# ============================================================================
# ML PREDICTOR CLASS
# ============================================================================

class MLPredictor:
    """
    Predicts price direction using machine learning.
    
    Algorithm:
    - Linear regression on technical features
    - Features: Returns, MA, Volatility, Volume ratio
    - Output: Direction (UP/DOWN/NEUTRAL) with confidence
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize with OHLCV price data.
        
        Args:
            data: DataFrame with ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self.model = LinearRegression()
        self.scaler = MinMaxScaler()
        self.trained = False
        self.prediction: Optional[str] = None
        self.confidence: float = 0.0
    
    # ========================================================================
    # FEATURE ENGINEERING
    # ========================================================================
    
    def _create_features(self, lookback_days: int = 20) -> Tuple[pd.DataFrame, list]:
        """
        Create predictive features from price data.
        
        Features:
        - Returns: Daily percentage change
        - MA_5: 5-day moving average
        - MA_20: 20-day moving average
        - Volatility: Rolling standard deviation of returns
        - Volume_Ratio: Current volume vs. moving average
        
        Args:
            lookback_days: Period for volatility calculation
            
        Returns:
            Tuple of (feature_df, feature_columns)
        """
        df = self.data.copy()
        
        # Price features
        df['Returns'] = df['Close'].pct_change()
        df['MA_5'] = df['Close'].rolling(5).mean()
        df['MA_20'] = df['Close'].rolling(20).mean()
        df['Volatility'] = df['Returns'].rolling(lookback_days).std()
        
        # Volume features
        df['Volume_MA'] = df['Volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA'].replace(0, 1)
        
        # Remove NaN rows
        df = df.dropna()
        
        feature_columns = [
            'Returns',
            'MA_5',
            'MA_20',
            'Volatility',
            'Volume_Ratio'
        ]
        
        return df, feature_columns
    
    # ========================================================================
    # MODEL TRAINING
    # ========================================================================
    
    def train(self, lookback_days: int = 20, min_samples: int = 10) -> bool:
        """
        Train the ML model on historical data.
        
        Args:
            lookback_days: Period for volatility/MA calculation
            min_samples: Minimum samples required to train
            
        Returns:
            True if training successful, False otherwise
        """
        try:
            df, feature_cols = self._create_features(lookback_days)
            
            # Need at least min_samples for training
            if len(df) < min_samples:
                return False
            
            # Prepare X (features) and y (target)
            X = df[feature_cols].values
            y_temp = df['Returns'].shift(-1).dropna().values
            y = np.array(y_temp, dtype=float)
            X = X[:-1]  # Remove last row (no target)
            
            # Normalize features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train model
            self.model.fit(X_scaled, y)
            self.trained = True
            return True
            
        except Exception as e:
            print(f"ML Training Error: {e}")
            return False
    
    # ========================================================================
    # PREDICTION
    # ========================================================================
    
    def predict_direction(self) -> Tuple[str, float]:
        """
        Predict next day's price direction.
        
        Returns:
            Tuple of (direction, confidence)
            - direction: 'UP', 'DOWN', or 'NEUTRAL'
            - confidence: 0.0 to 1.0
        """
        if not self.trained:
            self.prediction = 'UNKNOWN'
            self.confidence = 0.0
            return self.prediction, self.confidence
        
        try:
            df, feature_cols = self._create_features()
            
            if len(df) == 0:
                return 'UNKNOWN', 0.0
            
            # Get latest features
            latest_features = df[feature_cols].iloc[-1:].values
            latest_features_scaled = self.scaler.transform(latest_features)
            
            # Predict return
            predicted_return = self.model.predict(latest_features_scaled)[0]
            
            # Calculate confidence based on volatility
            recent_volatility = df['Volatility'].iloc[-1]
            # Higher volatility = lower confidence
            confidence = max(0.0, min(1.0, 0.5 - recent_volatility))
            
            # Determine direction
            if predicted_return > 0.001:  # Threshold to avoid noise
                direction = 'UP'
            elif predicted_return < -0.001:
                direction = 'DOWN'
            else:
                direction = 'NEUTRAL'
            
            self.prediction = direction
            self.confidence = confidence
            
            return direction, confidence
            
        except Exception as e:
            print(f"Prediction Error: {e}")
            return 'UNKNOWN', 0.0
    
    def get_predicted_price_change(self) -> float:
        """
        Get predicted percentage price change for next period.
        
        Returns:
            Predicted change as percentage (-1.0 to 1.0 represents -100% to +100%)
        """
        if not self.trained:
            return 0.0
        
        try:
            df, feature_cols = self._create_features()
            
            if len(df) == 0:
                return 0.0
            
            latest_features = df[feature_cols].iloc[-1:].values
            latest_features_scaled = self.scaler.transform(latest_features)
            
            predicted_return = self.model.predict(latest_features_scaled)[0]
            return predicted_return
            
        except Exception as e:
            print(f"Price Change Error: {e}")
            return 0.0
