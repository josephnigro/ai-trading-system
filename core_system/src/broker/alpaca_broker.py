"""
Alpaca Broker Integration — Paper & Live Trading via alpaca-py SDK.

Environment variables (from .env):
    ALPACA_API_KEY          — Paper trading key
    ALPACA_API_SECRET       — Paper trading secret
    ALPACA_LIVE_KEY         — Live trading key (BACKUP, keep commented until ready)
    ALPACA_LIVE_SECRET      — Live trading secret
    ALPACA_PAPER            — "true" (default) or "false" for live

Usage:
    from src.broker import AlpacaBroker
    broker = AlpacaBroker()          # reads from env, paper by default
    broker.validate()                 # confirms connection + prints balance
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime

from ..execution_module.execution_engine import BrokerIntegration


logger = logging.getLogger("AlpacaBroker")


def _paper_mode() -> bool:
    return os.getenv("ALPACA_PAPER", "true").strip().lower() in {"1", "true", "yes", "y"}


class AlpacaBroker(BrokerIntegration):
    """
    Alpaca broker implementation.

    All orders go to the paper trading endpoint unless ALPACA_PAPER=false.
    The SDK and credentials are loaded lazily on first use so that importing
    this module does not fail when alpaca-py is absent.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        paper: Optional[bool] = None,
    ):
        super().__init__("AlpacaBroker")
        self._paper = _paper_mode() if paper is None else paper

        if self._paper:
            self._api_key = api_key or os.getenv("ALPACA_API_KEY", "")
            self._api_secret = api_secret or os.getenv("ALPACA_API_SECRET", "")
        else:
            self._api_key = api_key or os.getenv("ALPACA_LIVE_KEY", "")
            self._api_secret = api_secret or os.getenv("ALPACA_LIVE_SECRET", "")

        self._trading_client = None
        self._data_client = None
        self._account = None

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_trading_client(self):
        """Lazily initialise the Alpaca TradingClient."""
        if self._trading_client is None:
            from alpaca.trading.client import TradingClient  # type: ignore
            self._trading_client = TradingClient(
                api_key=self._api_key,
                secret_key=self._api_secret,
                paper=self._paper,
            )
        return self._trading_client

    def _get_data_client(self):
        """Lazily initialise the Alpaca StockHistoricalDataClient."""
        if self._data_client is None:
            from alpaca.data.historical import StockHistoricalDataClient  # type: ignore
            self._data_client = StockHistoricalDataClient(
                api_key=self._api_key,
                secret_key=self._api_secret,
            )
        return self._data_client

    # ── BrokerIntegration interface ────────────────────────────────────────────

    def place_buy_order(
        self,
        symbol: str,
        shares: int,
        limit_price: Optional[float] = None,
    ) -> Dict:
        """
        Place a market (or limit) buy order via Alpaca.

        Returns a dict with keys: success, order_id, price, error
        """
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest  # type: ignore
            from alpaca.trading.enums import OrderSide, TimeInForce  # type: ignore

            client = self._get_trading_client()

            if limit_price:
                req = LimitOrderRequest(
                    symbol=symbol,
                    qty=shares,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    limit_price=round(limit_price, 2),
                )
            else:
                req = MarketOrderRequest(
                    symbol=symbol,
                    qty=shares,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                )

            order = client.submit_order(req)
            fill_price = float(order.filled_avg_price) if order.filled_avg_price else (limit_price or 0.0)
            mode = "PAPER" if self._paper else "LIVE"
            logger.info(f"[{mode}] BUY {shares} {symbol} → order {order.id}")
            return {
                "success": True,
                "order_id": str(order.id),
                "price": fill_price,
                "status": str(order.status),
            }
        except Exception as exc:
            logger.error(f"place_buy_order failed for {symbol}: {exc}")
            return {"success": False, "order_id": None, "price": 0.0, "error": str(exc)}

    def place_sell_order(
        self,
        symbol: str,
        shares: int,
        limit_price: Optional[float] = None,
    ) -> Dict:
        """
        Place a market (or limit) sell order via Alpaca.
        """
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest  # type: ignore
            from alpaca.trading.enums import OrderSide, TimeInForce  # type: ignore

            client = self._get_trading_client()

            if limit_price:
                req = LimitOrderRequest(
                    symbol=symbol,
                    qty=shares,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                    limit_price=round(limit_price, 2),
                )
            else:
                req = MarketOrderRequest(
                    symbol=symbol,
                    qty=shares,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                )

            order = client.submit_order(req)
            fill_price = float(order.filled_avg_price) if order.filled_avg_price else (limit_price or 0.0)
            mode = "PAPER" if self._paper else "LIVE"
            logger.info(f"[{mode}] SELL {shares} {symbol} → order {order.id}")
            return {
                "success": True,
                "order_id": str(order.id),
                "price": fill_price,
                "status": str(order.status),
            }
        except Exception as exc:
            logger.error(f"place_sell_order failed for {symbol}: {exc}")
            return {"success": False, "order_id": None, "price": 0.0, "error": str(exc)}

    def cancel_order(self, order_id: str) -> bool:
        try:
            import uuid  # noqa
            client = self._get_trading_client()
            client.cancel_order_by_id(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as exc:
            logger.error(f"cancel_order failed: {exc}")
            return False

    def get_balance(self) -> float:
        """Return buying power (cash available) from Alpaca account."""
        try:
            client = self._get_trading_client()
            account = client.get_account()
            return float(account.buying_power)
        except Exception as exc:
            logger.error(f"get_balance failed: {exc}")
            return 0.0

    def get_account_info(self) -> Dict:
        """Return full account summary."""
        try:
            client = self._get_trading_client()
            account = client.get_account()
            return {
                "account_number": account.account_number,
                "status": str(account.status),
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "equity": float(account.equity),
                "paper": self._paper,
            }
        except Exception as exc:
            logger.error(f"get_account_info failed: {exc}")
            return {}

    def get_all_positions(self) -> list:
        """Return list of all open positions."""
        try:
            client = self._get_trading_client()
            positions = client.get_all_positions()
            result = []
            for pos in positions:
                result.append({
                    "ticker": pos.symbol,
                    "shares": int(float(pos.qty)),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price) if pos.current_price else 0.0,
                    "market_value": float(pos.market_value) if pos.market_value else 0.0,
                    "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else 0.0,
                    "unrealized_plpc": float(pos.unrealized_plpc) if pos.unrealized_plpc else 0.0,
                    "side": str(pos.side),
                })
            return result
        except Exception as exc:
            logger.error(f"get_all_positions failed: {exc}")
            return []

    def get_position(self, symbol: str) -> Optional[Dict]:
        """Return a single open position, or None if not held."""
        try:
            client = self._get_trading_client()
            pos = client.get_open_position(symbol)
            return {
                "ticker": pos.symbol,
                "shares": int(float(pos.qty)),
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price) if pos.current_price else 0.0,
                "market_value": float(pos.market_value) if pos.market_value else 0.0,
                "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else 0.0,
                "unrealized_plpc": float(pos.unrealized_plpc) if pos.unrealized_plpc else 0.0,
                "side": str(pos.side),
            }
        except Exception:
            return None

    def close_position(self, symbol: str) -> Dict:
        """Close an entire position at market."""
        try:
            client = self._get_trading_client()
            order = client.close_position(symbol)
            logger.info(f"Closed position: {symbol} → order {order.id}")
            return {"success": True, "order_id": str(order.id)}
        except Exception as exc:
            logger.error(f"close_position failed for {symbol}: {exc}")
            return {"success": False, "error": str(exc)}

    def is_market_open(self) -> bool:
        """Return True if the US equity market is currently open."""
        try:
            client = self._get_trading_client()
            clock = client.get_clock()
            return bool(clock.is_open)
        except Exception as exc:
            logger.error(f"is_market_open failed: {exc}")
            return False

    def validate(self) -> bool:
        """Confirm connection by fetching account info."""
        if not self._api_key or not self._api_secret:
            self.log_error("Alpaca credentials not configured")
            return False
        try:
            info = self.get_account_info()
            if not info:
                return False
            mode = "PAPER" if self._paper else "LIVE"
            logger.info(
                f"Alpaca [{mode}] connected — "
                f"Account: {info.get('account_number')} | "
                f"Cash: ${float(info.get('cash', 0)):,.2f} | "
                f"Portfolio: ${float(info.get('portfolio_value', 0)):,.2f}"
            )
            return True
        except Exception as exc:
            self.log_error(f"Alpaca validate failed: {exc}")
            return False
