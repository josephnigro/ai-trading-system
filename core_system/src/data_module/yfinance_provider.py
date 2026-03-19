"""
Data module implementation using yfinance.
Refactored from existing data_engine.py
"""

import yfinance as yf
import pandas as pd
from typing import Optional, Dict
from datetime import datetime, time
import pytz

from ..core.data_interface import IDataProvider


class YFinanceDataProvider(IDataProvider):
    """
    Data provider using yfinance API.
    Fetches stock data from Yahoo Finance.
    """
    
    def __init__(self, name: str = "YFinanceProvider"):
        super().__init__(name)
        self.cache_ttl = 3600  # 1 hour
    
    def fetch_ohlcv(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from yfinance."""
        try:
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                threads=False
            )
            
            if data is None or len(data) == 0:
                self.log_error(f"No data returned for {ticker}")
                return None
            
            # Validate data
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_cols):
                self.log_error(f"Missing required columns for {ticker}")
                return None
            
            return data
        
        except Exception as e:
            self.log_error(f"Failed to fetch {ticker}: {str(e)}")
            return None
    
    def fetch_quote(self, ticker: str) -> Optional[Dict]:
        """Fetch current quote for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info:
                self.log_error(f"No quote data for {ticker}")
                return None
            
            return {
                'ticker': ticker,
                'price': info.get('currentPrice', 0),
                'bid': info.get('bid', 0),
                'ask': info.get('ask', 0),
                'volume': info.get('volume', 0),
                'market_cap': info.get('marketCap', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            self.log_error(f"Failed to fetch quote for {ticker}: {str(e)}")
            return None
    
    def is_market_open(self) -> bool:
        """Check if US stock market is open."""
        try:
            # US market (EST)
            eastern = pytz.timezone('US/Eastern')
            now = datetime.now(eastern)
            
            # Market hours: 9:30 AM - 4:00 PM EST, weekdays only
            market_open = now.weekday() < 5  # Monday-Friday
            market_open = market_open and time(9, 30) <= now.time() <= time(16, 0)
            
            return market_open
        
        except Exception:
            return False
    
    def validate(self) -> bool:
        """Validate provider is working."""
        try:
            # Test with a well-known ticker
            data = self.fetch_ohlcv("AAPL", period="1mo", interval="1d")
            return data is not None and len(data) > 0
        
        except Exception as e:
            self.log_error(f"Validation failed: {str(e)}")
            return False
