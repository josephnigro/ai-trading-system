"""Machine Learning price prediction using linear regression."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler


class MLPredictor:
    """Predicts price direction using ML on technical features."""
    
    def __init__(self, data):
        self.data = data.copy()
        self.model = LinearRegression()
        self.scaler = MinMaxScaler()
        self.prediction = None
        self.confidence = 0
        self.trained = False
    
    def create_features(self):
        """Create features from price data."""
        df = self.data.copy()
        
        df['Returns'] = df['Close'].pct_change()
        df['MA_5'] = df['Close'].rolling(5).mean()
        df['MA_20'] = df['Close'].rolling(20).mean()
        df['Volatility'] = df['Returns'].rolling(20).std()
        df['Volume_MA'] = df['Volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        df = df.dropna()
        feature_cols = ['Returns', 'MA_5', 'MA_20', 'Volatility', 'Volume_Ratio']
        
        return df, feature_cols
    
    def train(self, lookback_days=30):
        """Train the ML model."""
        df, feature_cols = self.create_features()
        
        if len(df) < 10:
            return False
        
        X = df[feature_cols].values
        y = df['Returns'].shift(-1).dropna().values
        X = X[:-1]
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.trained = True
        return True
    
    def predict_direction(self):
        """Predict next day's price direction."""
        if not self.trained:
            return 'UNKNOWN', 0
        
        df, feature_cols = self.create_features()
        
        latest_features = df[feature_cols].iloc[-1:].values
        latest_features_scaled = self.scaler.transform(latest_features)
        
        prediction = self.model.predict(latest_features_scaled)[0]
        
        recent_volatility = df['Volatility'].iloc[-1]
        confidence = max(0, min(1, 0.5 - recent_volatility))
        
        direction = (
            'UP' if prediction > 0 
            else 'DOWN' if prediction < 0 
            else 'NEUTRAL'
        )
        self.prediction = direction
        self.confidence = confidence
        
        return direction, confidence
    
    def get_predicted_price_change(self):
        """Get predicted percentage change."""
        if not self.trained:
            return 0
        
        df, feature_cols = self.create_features()
        latest_features = df[feature_cols].iloc[-1:].values
        latest_features_scaled = self.scaler.transform(latest_features)
        
        return self.model.predict(latest_features_scaled)[0] * 100
