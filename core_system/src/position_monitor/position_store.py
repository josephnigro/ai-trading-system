"""
Position store — persists open positions with their stop/target levels.

Written to logs/positions/open_positions.json by the orchestrator after each
execution, read by PositionMonitor during every monitoring check.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("PositionStore")

_DEFAULT_PATH = Path("logs/positions/open_positions.json")


class PositionStore:
    """Simple JSON-backed store for open positions."""

    def __init__(self, store_path: Optional[str] = None):
        self.path = Path(store_path) if store_path else _DEFAULT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _load(self) -> Dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error(f"PositionStore load failed: {exc}")
            return {}

    def _save(self, data: Dict[str, dict]) -> None:
        try:
            self.path.write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )
        except Exception as exc:
            logger.error(f"PositionStore save failed: {exc}")

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_position(
        self,
        ticker: str,
        shares: int,
        entry_price: float,
        stop_loss: float,
        profit_target: float,
        trade_id: str = "",
        order_id: str = "",
        notes: str = "",
    ) -> None:
        """Record a newly opened position."""
        data = self._load()
        data[ticker] = {
            "ticker": ticker,
            "shares": shares,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "profit_target": profit_target,
            "trade_id": trade_id,
            "order_id": order_id,
            "notes": notes,
            "opened_at": datetime.utcnow().isoformat(),
            "alert_stop_sent": False,
            "alert_target_sent": False,
        }
        self._save(data)
        logger.info(f"Position stored: {ticker} x{shares} entry={entry_price:.2f} "
                    f"stop={stop_loss:.2f} target={profit_target:.2f}")

    def remove_position(self, ticker: str) -> bool:
        """Remove a closed position from the store."""
        data = self._load()
        if ticker not in data:
            return False
        del data[ticker]
        self._save(data)
        logger.info(f"Position removed from store: {ticker}")
        return True

    def mark_alert_sent(self, ticker: str, alert_type: str) -> None:
        """Record that stop/target alert was already dispatched."""
        data = self._load()
        if ticker in data:
            data[ticker][f"alert_{alert_type}_sent"] = True
            self._save(data)

    def get_all(self) -> List[dict]:
        return list(self._load().values())

    def get(self, ticker: str) -> Optional[dict]:
        return self._load().get(ticker)
