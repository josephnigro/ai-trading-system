"""
Data module - handles all market data fetching and caching.
"""

from abc import abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime

from .base_module import BaseModule


class IDataProvider(BaseModule):
    """Interface for data providers."""
    
    @abstractmethod
    def fetch_ohlcv(
        self, 
        ticker: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for a ticker.
        
        Args:
            ticker: Stock ticker
            period: Time period ("1d", "1mo", "1y", etc.)
            interval: Candle interval ("1m", "5m", "1h", "1d", etc.)
        
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        pass
    
    @abstractmethod
    def fetch_quote(self, ticker: str) -> Optional[Dict]:
        """
        Fetch current quote for a ticker.
        
        Args:
            ticker: Stock ticker
        
        Returns:
            Dict with current price info or None if failed
        """
        pass
    
    @abstractmethod
    def is_market_open(self) -> bool:
        """Check if US stock market is currently open."""
        pass


class DataModule(BaseModule):
    """
    Main data module.
    
    - Fetches market data
    - Manages caching
    - Validates data quality
    """
    
    def __init__(self, provider: IDataProvider, enable_cache: bool = True):
        """
        Initialize data module.
        
        Args:
            provider: Data provider implementation
            enable_cache: Whether to use caching
        """
        super().__init__("DataModule")
        self.provider = provider
        self.cache = {} if enable_cache else None
    
    def initialize(self) -> bool:
        """Initialize and test data provider."""
        if not self.provider.initialize():
            self.log_error("Failed to initialize data provider")
            return False
        
        if not self.provider.validate():
            self.log_error("Data provider validation failed")
            return False
        
        return super().initialize()
    
    def get_ohlcv(
        self, 
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Get OHLCV data (with caching).
        
        Args:
            ticker: Stock ticker
            period: Time period
            interval: Candle interval
            use_cache: Whether to use cached data
        
        Returns:
            DataFrame or None
        """
        cache_key = f"{ticker}_{period}_{interval}"
        
        # Check cache
        if use_cache and self.cache and cache_key in self.cache:
            return self.cache[cache_key]
        
        # Fetch from provider
        data = self.provider.fetch_ohlcv(ticker, period, interval)
        
        if data is None:
            self.log_error(f"Failed to fetch OHLCV for {ticker}")
            return None
        
        # Cache result
        if self.cache is not None:
            self.cache[cache_key] = data
        
        return data
    
    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Get current quote."""
        return self.provider.fetch_quote(ticker)

    def get_data(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        use_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Get both OHLCV data and quote in one call.

        Returns:
            Dict with keys {"data", "quote"} or None if either payload is unavailable.
        """
        data = self.get_ohlcv(ticker, period=period, interval=interval, use_cache=use_cache)
        if data is None:
            return None

        quote = self.get_quote(ticker)
        if quote is None:
            return None

        return {
            'data': data,
            'quote': quote,
        }
    
    def validate(self) -> bool:
        """Validate module is working."""
        return self.provider.validate()
