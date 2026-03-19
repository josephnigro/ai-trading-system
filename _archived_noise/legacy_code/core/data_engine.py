"""Data fetching and management from Alpha Vantage."""

import pandas as pd
import sys
import os

# Add parent directory to path to import alpha_vantage_engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alpha_vantage_engine import AlphaVantageEngine


class DataEngine:
    """Fetches and manages stock data from Alpha Vantage."""
    
    def __init__(self, tickers, api_key=None):
        self.tickers = tickers
        self.data = {}
        self.engine = AlphaVantageEngine(api_key=api_key)

    def fetch_data(self, period="3mo", interval="1d"):
        """Fetch stock data for all tickers from Alpha Vantage."""
        # Convert period to days
        days_map = {
            "3mo": 63,
            "6mo": 126,
            "1y": 252,
            "2y": 504
        }
        days = days_map.get(period, 252)
        
        self.data = self.engine.fetch_data(self.tickers, days=days)
        return self.data

    def get_latest_price(self, ticker):
        """Get most recent closing price."""
        try:
            return self.data[ticker]["Close"].iloc[-1]
        except (KeyError, IndexError):
            return None

    def get_volume(self, ticker):
        """Get latest volume."""
        try:
            return self.data[ticker]["Volume"].iloc[-1]
        except (KeyError, IndexError):
            return None

    def summary(self):
        """Print quick summary of fetched data."""
        print("\n=== DATA SUMMARY (Alpha Vantage) ===")
        for ticker in self.data:
            price = self.get_latest_price(ticker)
            volume = self.get_volume(ticker)
            if price and volume:
                print(f"{ticker} | Price: ${price:.2f} | Volume: {volume:,.0f}")

