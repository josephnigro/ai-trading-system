# ==============================
# DATA ENGINE MODULE
# ==============================

import pandas as pd
from datetime import datetime
from alpha_vantage_engine import AlphaVantageEngine

class DataEngine:
    def __init__(self, tickers, api_key=None):
        self.tickers = tickers
        self.data = {}
        self.engine = AlphaVantageEngine(api_key=api_key)

    def fetch_data(self, period="3mo", interval="1d"):
        """
        Fetch stock data from Alpha Vantage
        period: "3mo", "1y" (interval '1d' is default, only option supported)
        """
        # Convert period to days for Alpha Vantage
        days_map = {
            "3mo": 63,
            "6mo": 126,
            "1y": 252,
            "2y": 504
        }
        days = days_map.get(period, 252)
        
        # Fetch data from Alpha Vantage
        self.data = self.engine.fetch_data(self.tickers, days=days)
        return self.data

    def get_latest_price(self, ticker):
        """
        Get most recent closing price
        """
        try:
            return self.data[ticker]["Close"].iloc[-1]
        except:
            return None

    def get_volume(self, ticker):
        """
        Get latest volume
        """
        try:
            return self.data[ticker]["Volume"].iloc[-1]
        except:
            return None

    def summary(self):
        """
        Print quick summary
        """
        print("\n=== DATA SUMMARY ===")
        for ticker in self.data:
            price = self.get_latest_price(ticker)
            volume = self.get_volume(ticker)
            print(f"{ticker} | Price: {price:.2f} | Volume: {volume}")