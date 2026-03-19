"""
# ============================================================================
# DATA ENGINE - UNIFIED DATA FETCHING INTERFACE
# ============================================================================
# Wrapper around data sources (Alpha Vantage) with caching and utilities
# ============================================================================
"""

from typing import Dict, Optional, List
import pandas as pd
from datetime import datetime
from .alpha_vantage import AlphaVantageAPI


# ============================================================================
# DATA ENGINE CLASS
# ============================================================================

class DataEngine:
    """
    Unified interface for fetching and managing stock market data.
    
    Features:
    - Fetches data from Alpha Vantage API
    - Caches results to minimize API calls
    - Period mapping (3mo, 6mo, 1y, 2y)
    - Utility methods for quick lookups
    """
    
    # Period to days mapping
    PERIOD_DAYS_MAP = {
        '1w': 5,
        '1mo': 21,
        '3mo': 63,
        '6mo': 126,
        '1y': 252,
        '2y': 504,
    }
    
    def __init__(self, tickers: List[str], api_key: Optional[str] = None):
        """
        Initialize data engine with ticker list.
        
        Args:
            tickers: List of stock symbols to track
            api_key: Alpha Vantage API key (optional, defaults to env var)
        """
        self.tickers = tickers
        self.api_engine = AlphaVantageAPI(api_key=api_key)
        self.data: Dict[str, pd.DataFrame] = {}
    
    # ========================================================================
    # DATA FETCHING
    # ========================================================================
    
    def fetch_data(
        self,
        period: str = "1y",
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for all configured tickers.
        
        Args:
            period: Time period ('1w', '1mo', '3mo', '6mo', '1y', '2y')
            interval: Interval (currently only '1d' supported)
            
        Returns:
            Dictionary mapping ticker -> DataFrame
        """
        days = self.PERIOD_DAYS_MAP.get(period, 252)
        
        print(f"\nFetching {period} ({days} days) of data for {len(self.tickers)} tickers...")
        print("-" * 60)
        
        self.data = self.api_engine.fetch_data(self.tickers, days=days)
        
        return self.data
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_latest_price(self, ticker: str) -> Optional[float]:
        """Get most recent closing price for a ticker."""
        try:
            if ticker in self.data:
                return float(self.data[ticker]['Close'].iloc[-1])
            return None
        except (KeyError, IndexError, ValueError):
            return None
    
    def get_volume(self, ticker: str) -> Optional[int]:
        """Get latest trading volume for a ticker."""
        try:
            if ticker in self.data:
                return int(self.data[ticker]['Volume'].iloc[-1])
            return None
        except (KeyError, IndexError, ValueError):
            return None
    
    def get_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Get full data DataFrame for a ticker."""
        return self.data.get(ticker, None)
    
    def has_data(self, ticker: str) -> bool:
        """Check if data is available for ticker."""
        return ticker in self.data and not self.data[ticker].empty
    
    def summary(self) -> None:
        """Print summary of fetched data."""
        if not self.data:
            print("No data available")
            return
        
        print("\n" + "="*70)
        print("DATA ENGINE SUMMARY")
        print("="*70)
        print(f"{'Ticker':<8} {'Price':>12} {'Volume':>15} {'Days':<8}")
        print("-"*70)
        
        for ticker in sorted(self.data.keys()):
            price = self.get_latest_price(ticker)
            volume = self.get_volume(ticker)
            days = len(self.data[ticker]) if self.has_data(ticker) else 0
            
            if price is not None:
                print(f"{ticker:<8} ${price:>11.2f} {volume:>15,.0f} {days:<8}")
        
        print("="*70 + "\n")
