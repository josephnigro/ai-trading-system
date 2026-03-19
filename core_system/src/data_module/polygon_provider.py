"""Polygon-first data provider with automatic yfinance fallback."""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from ..core.data_interface import IDataProvider
from .yfinance_provider import YFinanceDataProvider


class PolygonFallbackDataProvider(IDataProvider):
    """
    Polygon as primary source, yfinance as fallback.

    This provider preserves the existing data contract expected by the
    orchestrator and downstream modules.
    """

    _BASE_URL = "https://api.polygon.io"
    _MIN_CALL_INTERVAL_SECONDS = 0.3  # polite pacing for free-tier limits

    def __init__(
        self,
        api_key: Optional[str] = None,
        fallback_provider: Optional[YFinanceDataProvider] = None,
        name: str = "PolygonFallbackDataProvider",
    ):
        super().__init__(name)
        self.api_key = (
            api_key
            or os.getenv("POLYGON_API_KEY", "").strip()
            or os.getenv("POLYGONIO_API_KEY", "").strip()
        )
        self.fallback = fallback_provider or YFinanceDataProvider()
        self._last_call_ts = 0.0
        self._market_cap_cache: Dict[str, int] = {}
        self._polygon_disabled_until = 0.0

    def initialize(self) -> bool:
        """Initialize fallback provider and mark this provider initialized."""
        if not self.fallback.initialize():
            self.log_error("Fallback provider initialization failed")
            return False
        return super().initialize()

    def fetch_ohlcv(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV, trying Polygon first and yfinance on failure."""
        polygon_data = self._fetch_polygon_ohlcv(ticker, period=period, interval=interval)
        if polygon_data is not None:
            self.logger.info(f"{ticker}: data from polygon")
            return polygon_data

        self.logger.info(f"{ticker}: polygon failed, using yfinance")
        fallback_data = self.fallback.fetch_ohlcv(ticker, period=period, interval=interval)
        if fallback_data is not None:
            self.logger.info(f"{ticker}: data from yfinance")
            return fallback_data

        self.logger.info(f"{ticker}: no valid data")
        return None

    def fetch_quote(self, ticker: str) -> Optional[Dict]:
        """Fetch quote dict with Polygon first and yfinance fallback."""
        polygon_quote = self._fetch_polygon_quote(ticker)
        if polygon_quote is not None:
            self.logger.info(f"{ticker}: quote from polygon")
            return polygon_quote

        self.logger.info(f"{ticker}: polygon quote failed, using yfinance")
        fallback_quote = self.fallback.fetch_quote(ticker)
        if fallback_quote is not None:
            return fallback_quote

        self.logger.info(f"{ticker}: no valid data")
        return None

    def is_market_open(self) -> bool:
        """Reuse fallback market-hours check."""
        return self.fallback.is_market_open()

    def validate(self) -> bool:
        """Validate by checking that fallback can provide valid data."""
        if self.api_key:
            polygon_probe = self._fetch_polygon_ohlcv("AAPL", period="3mo", interval="1d")
            if polygon_probe is not None and len(polygon_probe) > 0:
                return True
        return self.fallback.validate()

    # Internal helpers

    def _rate_limit_wait(self) -> None:
        """Small delay between Polygon requests to avoid free-tier bursts."""
        elapsed = time.time() - self._last_call_ts
        if elapsed < self._MIN_CALL_INTERVAL_SECONDS:
            time.sleep(self._MIN_CALL_INTERVAL_SECONDS - elapsed)
        self._last_call_ts = time.time()

    def _polygon_get(self, path: str, params: Dict[str, str]) -> Optional[Dict]:
        """Perform a Polygon GET request and decode JSON safely."""
        if not self.api_key:
            return None
        if time.time() < self._polygon_disabled_until:
            return None

        self._rate_limit_wait()
        full_params = dict(params)
        full_params["apiKey"] = self.api_key
        url = f"{self._BASE_URL}{path}?{urlencode(full_params)}"

        try:
            with urlopen(url, timeout=12) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except HTTPError as exc:
            status = getattr(exc, "code", None)
            if status == 429:
                # Free-tier burst limit hit: cool down briefly and fallback.
                self._polygon_disabled_until = time.time() + 90
            elif status == 403:
                # Unauthorized/plan restriction: disable longer to avoid noisy retries.
                self._polygon_disabled_until = time.time() + 600
            self.log_error(f"Polygon request failed for {path}: {exc}")
            return None
        except (URLError, TimeoutError) as exc:
            self.log_error(f"Polygon request failed for {path}: {exc}")
            return None
        except Exception as exc:
            self.log_error(f"Polygon decode/processing failed for {path}: {exc}")
            return None

    def _fetch_polygon_ohlcv(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch daily OHLCV from Polygon aggregates.

        Free-tier-safe behavior:
        - Uses REST aggregates endpoint.
        - Requests daily bars.
        - Caps lookback window to about 3 months for reliability and rate control.
        """
        if interval != "1d":
            return None

        end_dt = datetime.utcnow().date()
        period_days = {
            "1d": 1,
            "5d": 5,
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825,
        }.get(period, 90)

        lookback_days = min(period_days, 95)
        start_dt = end_dt - timedelta(days=lookback_days)

        data = self._polygon_get(
            f"/v2/aggs/ticker/{ticker.upper()}/range/1/day/{start_dt}/{end_dt}",
            {
                "adjusted": "true",
                "sort": "asc",
                "limit": "500",
            },
        )

        if not data:
            return None
        results = data.get("results", [])
        if not results:
            return None

        rows = []
        for bar in results:
            ts_ms = bar.get("t")
            if ts_ms is None:
                continue
            rows.append(
                {
                    "Date": datetime.utcfromtimestamp(ts_ms / 1000.0),
                    "Open": float(bar.get("o", 0.0)),
                    "High": float(bar.get("h", 0.0)),
                    "Low": float(bar.get("l", 0.0)),
                    "Close": float(bar.get("c", 0.0)),
                    "Volume": float(bar.get("v", 0.0)),
                }
            )

        if not rows:
            return None

        df = pd.DataFrame(rows).set_index("Date")
        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        if not all(col in df.columns for col in required_cols):
            return None

        return df[required_cols]

    def _fetch_polygon_quote(self, ticker: str) -> Optional[Dict]:
        """Fetch latest price and market cap from Polygon endpoints when possible."""
        ticker = ticker.upper()
        snapshot = self._polygon_get(
            f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}",
            {},
        )

        # Default quote shape expected by current orchestrator pipeline.
        quote = {
            "ticker": ticker,
            "price": 0.0,
            "bid": 0.0,
            "ask": 0.0,
            "volume": 0.0,
            "market_cap": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if snapshot and snapshot.get("status") == "OK":
            snap_ticker = snapshot.get("ticker", {})
            day = snap_ticker.get("day", {})
            last_trade = snap_ticker.get("lastTrade", {})
            last_quote = snap_ticker.get("lastQuote", {})

            quote["price"] = float(last_trade.get("p") or day.get("c") or 0.0)
            quote["bid"] = float(last_quote.get("p") or 0.0)
            quote["ask"] = float(last_quote.get("P") or 0.0)
            quote["volume"] = float(day.get("v") or 0.0)

        if ticker in self._market_cap_cache:
            quote["market_cap"] = self._market_cap_cache[ticker]
        else:
            details = self._polygon_get(
                f"/v3/reference/tickers/{ticker}",
                {},
            )
            if details and details.get("status") == "OK":
                result = details.get("results", {})
                market_cap = result.get("market_cap", 0) if isinstance(result, dict) else 0
                try:
                    cached_cap = int(market_cap or 0)
                    self._market_cap_cache[ticker] = cached_cap
                    quote["market_cap"] = cached_cap
                except Exception:
                    quote["market_cap"] = 0

        if quote["price"] <= 0:
            return None

        return quote
