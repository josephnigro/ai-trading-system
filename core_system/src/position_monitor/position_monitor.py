"""
Position Monitor — Phase 5

Runs every hour during market hours to check all open positions:
  - Fetches live prices from Alpaca
  - Compares against stop loss and profit target
  - Sends email alert when either level is hit
  - Optionally auto-closes the position via Alpaca

Example standalone use:
    from src.position_monitor.position_monitor import PositionMonitor
    from src.broker.alpaca_broker import AlpacaBroker

    monitor = PositionMonitor(broker=AlpacaBroker())
    alerts = monitor.run_check()
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

from .position_store import PositionStore

logger = logging.getLogger("PositionMonitor")


class PositionAlert:
    """Container for a single position alert."""

    def __init__(
        self,
        ticker: str,
        alert_type: str,           # "stop_hit", "target_hit", "near_stop", "near_target"
        current_price: float,
        trigger_price: float,
        entry_price: float,
        shares: int,
        unrealized_pl: float,
        unrealized_pct: float,
        auto_closed: bool = False,
        close_order_id: str = "",
    ):
        self.ticker = ticker
        self.alert_type = alert_type
        self.current_price = current_price
        self.trigger_price = trigger_price
        self.entry_price = entry_price
        self.shares = shares
        self.unrealized_pl = unrealized_pl
        self.unrealized_pct = unrealized_pct
        self.auto_closed = auto_closed
        self.close_order_id = close_order_id
        self.triggered_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "alert_type": self.alert_type,
            "current_price": self.current_price,
            "trigger_price": self.trigger_price,
            "entry_price": self.entry_price,
            "shares": self.shares,
            "unrealized_pl": self.unrealized_pl,
            "unrealized_pct": self.unrealized_pct,
            "auto_closed": self.auto_closed,
            "close_order_id": self.close_order_id,
            "triggered_at": self.triggered_at.isoformat(),
        }


class PositionMonitor:
    """
    Monitors all open positions and fires alerts when stops/targets are hit.
    """

    def __init__(
        self,
        broker=None,
        store: Optional[PositionStore] = None,
        performance_tracker=None,
        auto_close_stops: bool = False,
        auto_close_targets: bool = False,
        near_stop_pct: float = 2.0,    # alert when within 2% of stop
        near_target_pct: float = 2.0,  # alert when within 2% of target
    ):
        """
        Args:
            broker:             AlpacaBroker instance (or None for price-only check via yfinance)
            store:              PositionStore (defaults to logs/positions/open_positions.json)
            performance_tracker: PerformanceTracker to record closed trades
            auto_close_stops:   Automatically close positions when stop is hit
            auto_close_targets: Automatically close positions when target is hit
            near_stop_pct:      Send "near stop" warning when within this % of stop
            near_target_pct:    Send "near target" alert when within this % of target
        """
        self.broker = broker
        self.store = store or PositionStore()
        self.performance_tracker = performance_tracker
        self.auto_close_stops = auto_close_stops
        self.auto_close_targets = auto_close_targets
        self.near_stop_pct = near_stop_pct
        self.near_target_pct = near_target_pct

    # ── Price fetching ─────────────────────────────────────────────────────────

    def _get_current_price(self, ticker: str) -> Optional[float]:
        """Fetch current price via Alpaca (preferred) or yfinance fallback."""
        # Try Alpaca first
        if self.broker is not None:
            position = self.broker.get_position(ticker)
            if position and position.get("current_price", 0) > 0:
                return float(position["current_price"])
            # Try live quote via trading client
            try:
                from alpaca.data.historical import StockHistoricalDataClient  # type: ignore
                from alpaca.data.requests import StockLatestQuoteRequest  # type: ignore
                client = self.broker._get_data_client()
                req = StockLatestQuoteRequest(symbol_or_symbols=ticker)
                quotes = client.get_stock_latest_quote(req)
                if ticker in quotes:
                    q = quotes[ticker]
                    mid = (float(q.ask_price) + float(q.bid_price)) / 2
                    if mid > 0:
                        return mid
            except Exception:
                pass

        # yfinance fallback
        try:
            import yfinance as yf  # type: ignore
            data = yf.download(ticker, period="1d", interval="1m", progress=False)
            if data is not None and not data.empty:
                close = data["Close"]
                if hasattr(close, "iloc"):
                    val = close.iloc[-1]
                    if hasattr(val, "item"):
                        return float(val.item())
                    return float(val)
        except Exception as exc:
            logger.warning(f"yfinance price fetch failed for {ticker}: {exc}")

        return None

    # ── Core check logic ───────────────────────────────────────────────────────

    def run_check(self, send_notifications: bool = False, notification_module=None) -> List[PositionAlert]:
        """
        Check all tracked positions against stop/target levels.

        Args:
            send_notifications:  If True, send email/SMS alerts via notification_module
            notification_module: NotificationModule instance for sending alerts

        Returns:
            List of PositionAlert objects that were triggered this run.
        """
        positions = self.store.get_all()
        if not positions:
            logger.info("Position monitor: no open positions to check")
            return []

        logger.info(f"Position monitor: checking {len(positions)} position(s)")
        alerts: List[PositionAlert] = []

        for pos in positions:
            ticker = pos["ticker"]
            entry = float(pos["entry_price"])
            stop = float(pos["stop_loss"])
            target = float(pos["profit_target"])
            shares = int(pos["shares"])
            alert_stop_sent = pos.get("alert_stop_sent", False)
            alert_target_sent = pos.get("alert_target_sent", False)

            current = self._get_current_price(ticker)
            if current is None:
                logger.warning(f"Could not fetch price for {ticker}, skipping")
                continue

            pl = (current - entry) * shares
            pl_pct = ((current - entry) / entry) * 100 if entry > 0 else 0.0

            logger.info(
                f"  {ticker}: entry={entry:.2f} current={current:.2f} "
                f"stop={stop:.2f} target={target:.2f} P&L={pl:+.2f} ({pl_pct:+.1f}%)"
            )

            alert: Optional[PositionAlert] = None

            # ── Stop loss hit ──────────────────────────────────────────────────
            if current <= stop and not alert_stop_sent:
                closed = False
                order_id = ""
                if self.auto_close_stops and self.broker:
                    result = self.broker.close_position(ticker)
                    closed = result.get("success", False)
                    order_id = result.get("order_id", "")
                    if closed:
                        if self.performance_tracker is not None:
                            self.performance_tracker.record_close_from_position(
                                pos,
                                exit_price=current,
                                exit_reason="stop_hit",
                            )
                        self.store.remove_position(ticker)
                    logger.warning(f"STOP HIT: {ticker} @ {current:.2f} (stop={stop:.2f})")

                alert = PositionAlert(
                    ticker=ticker, alert_type="stop_hit",
                    current_price=current, trigger_price=stop,
                    entry_price=entry, shares=shares,
                    unrealized_pl=pl, unrealized_pct=pl_pct,
                    auto_closed=closed, close_order_id=order_id,
                )
                self.store.mark_alert_sent(ticker, "stop")

            # ── Profit target hit ──────────────────────────────────────────────
            elif current >= target and not alert_target_sent:
                closed = False
                order_id = ""
                if self.auto_close_targets and self.broker:
                    result = self.broker.close_position(ticker)
                    closed = result.get("success", False)
                    order_id = result.get("order_id", "")
                    if closed:
                        if self.performance_tracker is not None:
                            self.performance_tracker.record_close_from_position(
                                pos,
                                exit_price=current,
                                exit_reason="target_hit",
                            )
                        self.store.remove_position(ticker)
                    logger.info(f"TARGET HIT: {ticker} @ {current:.2f} (target={target:.2f})")

                alert = PositionAlert(
                    ticker=ticker, alert_type="target_hit",
                    current_price=current, trigger_price=target,
                    entry_price=entry, shares=shares,
                    unrealized_pl=pl, unrealized_pct=pl_pct,
                    auto_closed=closed, close_order_id=order_id,
                )
                self.store.mark_alert_sent(ticker, "target")

            # ── Near stop warning (only once until price recovers) ─────────────
            elif not alert_stop_sent and stop > 0:
                dist_pct = ((current - stop) / stop) * 100
                if 0 < dist_pct <= self.near_stop_pct:
                    alert = PositionAlert(
                        ticker=ticker, alert_type="near_stop",
                        current_price=current, trigger_price=stop,
                        entry_price=entry, shares=shares,
                        unrealized_pl=pl, unrealized_pct=pl_pct,
                    )

            # ── Near target ────────────────────────────────────────────────────
            elif not alert_target_sent and target > 0:
                dist_pct = ((target - current) / target) * 100
                if 0 < dist_pct <= self.near_target_pct:
                    alert = PositionAlert(
                        ticker=ticker, alert_type="near_target",
                        current_price=current, trigger_price=target,
                        entry_price=entry, shares=shares,
                        unrealized_pl=pl, unrealized_pct=pl_pct,
                    )

            if alert:
                alerts.append(alert)

        # ── Send notifications ─────────────────────────────────────────────────
        if alerts and send_notifications and notification_module:
            notification_module.send_position_alerts(alerts)

        logger.info(f"Position monitor complete — {len(alerts)} alert(s) triggered")
        return alerts

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Return a current snapshot of all tracked positions with live prices."""
        positions = self.store.get_all()
        if not positions:
            return {"positions": [], "total_unrealized_pl": 0.0, "count": 0}

        rows = []
        total_pl = 0.0
        for pos in positions:
            ticker = pos["ticker"]
            entry = float(pos["entry_price"])
            shares = int(pos["shares"])
            current = self._get_current_price(ticker) or entry
            pl = (current - entry) * shares
            pl_pct = ((current - entry) / entry) * 100 if entry > 0 else 0.0
            total_pl += pl
            rows.append({
                "ticker": ticker,
                "shares": shares,
                "entry_price": entry,
                "current_price": current,
                "stop_loss": float(pos["stop_loss"]),
                "profit_target": float(pos["profit_target"]),
                "unrealized_pl": round(pl, 2),
                "unrealized_pct": round(pl_pct, 2),
            })

        return {
            "positions": rows,
            "total_unrealized_pl": round(total_pl, 2),
            "count": len(rows),
            "checked_at": datetime.now().isoformat(),
        }
