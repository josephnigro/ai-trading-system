"""
Performance Tracker — Phase 6

Persists every closed trade to a JSON ledger and computes live statistics:
  - Total P&L, win rate, average winner/loser
  - R-multiple per trade (how many R's were captured)
  - Sharpe ratio (annualised)
  - Max drawdown on the equity curve
  - Equity curve snapshots

The ledger lives at logs/performance/trade_ledger.json.
An equity snapshot is appended to logs/performance/equity_curve.json each time
a trade is closed.

Usage:
    tracker = PerformanceTracker()
    tracker.record_close(execution_record, exit_price=26.10, exit_reason="target_hit")
    stats = tracker.get_stats()
    html  = tracker.build_stats_html()  # for embedding in daily email
"""

import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PerformanceTracker")

_LEDGER_PATH = Path("logs/performance/trade_ledger.json")
_EQUITY_PATH = Path("logs/performance/equity_curve.json")


class PerformanceTracker:

    def __init__(
        self,
        ledger_path: Optional[str] = None,
        equity_path: Optional[str] = None,
        starting_equity: float = 100_000.0,
    ):
        self.ledger_path = Path(ledger_path) if ledger_path else _LEDGER_PATH
        self.equity_path = Path(equity_path) if equity_path else _EQUITY_PATH
        self.starting_equity = starting_equity
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.equity_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Internal I/O ───────────────────────────────────────────────────────────

    def _load_ledger(self) -> List[Dict]:
        if not self.ledger_path.exists():
            return []
        try:
            return json.loads(self.ledger_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error(f"Ledger load failed: {exc}")
            return []

    def _save_ledger(self, records: List[Dict]) -> None:
        try:
            self.ledger_path.write_text(
                json.dumps(records, indent=2, default=str), encoding="utf-8"
            )
        except Exception as exc:
            logger.error(f"Ledger save failed: {exc}")

    def _load_equity(self) -> List[Dict]:
        if not self.equity_path.exists():
            return []
        try:
            return json.loads(self.equity_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error(f"Equity load failed: {exc}")
            return []

    def _append_equity(self, point: Dict) -> None:
        curve = self._load_equity()
        curve.append(point)
        try:
            self.equity_path.write_text(
                json.dumps(curve, indent=2, default=str), encoding="utf-8"
            )
        except Exception as exc:
            logger.error(f"Equity save failed: {exc}")

    # ── Core API ───────────────────────────────────────────────────────────────

    def record_close(
        self,
        execution_record,
        exit_price: float,
        exit_reason: str = "manual",
    ) -> Dict:
        """
        Record a closed trade from an ExecutionRecord.

        Args:
            execution_record: ExecutionRecord instance (or dict)
            exit_price:       Price at which position was closed
            exit_reason:      "stop_hit", "target_hit", "manual", "time_stop"

        Returns:
            The trade record dict that was persisted.
        """
        # Accept either ExecutionRecord object or dict
        if hasattr(execution_record, "to_dict"):
            base = execution_record.to_dict()
        else:
            base = dict(execution_record)

        entry = float(base.get("execution_price") or base.get("entry_price") or 0.0)
        shares = int(base.get("shares", 0))
        signal_type = base.get("signal_type", "BUY")

        if signal_type in ("BUY", "COVER"):
            gross_pnl = (exit_price - entry) * shares
        else:
            gross_pnl = (entry - exit_price) * shares

        commission = float(base.get("commission", 0.0))
        net_pnl = gross_pnl - commission

        cost_basis = entry * shares if entry > 0 else 1.0
        pnl_pct = (net_pnl / cost_basis) * 100 if cost_basis > 0 else 0.0

        # R-multiple: how many times the initial risk was captured
        stop_loss = float(base.get("stop_loss", 0.0))
        risk_per_share = abs(entry - stop_loss) if stop_loss and entry else 0.0
        r_multiple = (net_pnl / (risk_per_share * shares)) if risk_per_share > 0 and shares > 0 else 0.0

        record = {
            "trade_id": base.get("trade_id", ""),
            "ticker": base.get("ticker", ""),
            "signal_type": signal_type,
            "shares": shares,
            "entry_price": entry,
            "exit_price": exit_price,
            "stop_loss": stop_loss,
            "profit_target": float(base.get("profit_target", 0.0)),
            "exit_reason": exit_reason,
            "gross_pnl": round(gross_pnl, 2),
            "commission": commission,
            "net_pnl": round(net_pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "r_multiple": round(r_multiple, 3),
            "hold_hours": base.get("hold_duration_hours") or 0.0,
            "opened_at": base.get("executed_at") or base.get("created_at") or datetime.utcnow().isoformat(),
            "closed_at": datetime.utcnow().isoformat(),
            "winner": net_pnl > 0,
        }

        records = self._load_ledger()
        records.append(record)
        self._save_ledger(records)

        # Equity snapshot
        stats = self._compute_stats(records)
        self._append_equity({
            "timestamp": record["closed_at"],
            "trade_number": len(records),
            "ticker": record["ticker"],
            "net_pnl": record["net_pnl"],
            "cumulative_pnl": round(stats["cumulative_pnl"], 2),
            "equity": round(self.starting_equity + stats["cumulative_pnl"], 2),
        })

        logger.info(
            f"Trade closed: {record['ticker']} | P&L ${net_pnl:+.2f} "
            f"({pnl_pct:+.1f}%) | R={r_multiple:+.2f} | Reason: {exit_reason}"
        )
        return record

    def record_close_from_position(
        self,
        position: Dict,
        exit_price: float,
        exit_reason: str = "manual",
    ) -> Dict:
        """
        Convenience method — record close directly from a PositionStore entry dict.
        """
        synthetic = {
            "trade_id": position.get("trade_id", ""),
            "ticker": position.get("ticker", ""),
            "signal_type": "BUY",
            "shares": position.get("shares", 0),
            "execution_price": position.get("entry_price", 0.0),
            "stop_loss": position.get("stop_loss", 0.0),
            "profit_target": position.get("profit_target", 0.0),
            "commission": 0.0,
            "executed_at": position.get("opened_at", datetime.utcnow().isoformat()),
        }
        return self.record_close(synthetic, exit_price, exit_reason)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def _compute_stats(self, records: List[Dict]) -> Dict[str, Any]:
        if not records:
            return self._empty_stats()

        pnls = [r["net_pnl"] for r in records]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p <= 0]
        r_multiples = [r["r_multiple"] for r in records]
        cumulative_pnl = sum(pnls)
        total_trades = len(records)
        win_rate = len(winners) / total_trades if total_trades else 0.0

        avg_win = sum(winners) / len(winners) if winners else 0.0
        avg_loss = sum(losers) / len(losers) if losers else 0.0
        avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        # Max drawdown on equity curve
        equity = self.starting_equity
        peak = equity
        max_dd = 0.0
        for p in pnls:
            equity += p
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        # Sharpe (annualised, assuming 252 trading days, 1 trade/day avg)
        if len(pnls) >= 2:
            mean_pnl = sum(pnls) / len(pnls)
            variance = sum((p - mean_pnl) ** 2 for p in pnls) / (len(pnls) - 1)
            std_pnl = math.sqrt(variance)
            sharpe = (mean_pnl / std_pnl) * math.sqrt(252) if std_pnl > 0 else 0.0
        else:
            sharpe = 0.0

        profit_factor = abs(sum(winners) / sum(losers)) if losers and sum(losers) != 0 else 0.0

        return {
            "total_trades": total_trades,
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": round(win_rate * 100, 1),
            "cumulative_pnl": round(cumulative_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_r_multiple": round(avg_r, 3),
            "expectancy": round(expectancy, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "current_equity": round(self.starting_equity + cumulative_pnl, 2),
            "total_return_pct": round((cumulative_pnl / self.starting_equity) * 100, 2),
        }

    def _empty_stats(self) -> Dict[str, Any]:
        return {
            "total_trades": 0, "winners": 0, "losers": 0, "win_rate": 0.0,
            "cumulative_pnl": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
            "avg_r_multiple": 0.0, "expectancy": 0.0, "profit_factor": 0.0,
            "max_drawdown_pct": 0.0, "sharpe_ratio": 0.0,
            "current_equity": self.starting_equity, "total_return_pct": 0.0,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return performance statistics for all closed trades."""
        return self._compute_stats(self._load_ledger())

    def get_recent_trades(self, n: int = 10) -> List[Dict]:
        """Return the n most recent closed trades."""
        return self._load_ledger()[-n:]

    def get_equity_curve(self) -> List[Dict]:
        """Return full equity curve data."""
        return self._load_equity()

    # ── HTML for email ─────────────────────────────────────────────────────────

    def build_stats_html(self) -> str:
        """
        Build an HTML block summarising performance metrics.
        Designed to be embedded in the daily digest email.
        """
        s = self.get_stats()
        if s["total_trades"] == 0:
            return (
                '<p style="font-family:Arial,sans-serif;font-size:13px;color:#78909c;'
                'text-align:center;padding:16px 0;">No closed trades yet.</p>'
            )

        pnl_color = "#2e7d32" if s["cumulative_pnl"] >= 0 else "#c62828"
        tr_color = "#2e7d32" if s["total_return_pct"] >= 0 else "#c62828"
        sharpe_color = "#2e7d32" if s["sharpe_ratio"] >= 1.0 else ("#fb8c00" if s["sharpe_ratio"] >= 0.5 else "#c62828")

        def _metric(label: str, value: str, color: str = "#0d1b2a") -> str:
            return (
                f'<td style="padding:10px 14px;text-align:center;border-right:1px solid #e0e0e0;">'
                f'<p style="font-family:Arial,sans-serif;font-size:11px;color:#90a4ae;margin:0 0 4px;text-transform:uppercase;letter-spacing:1px;">{label}</p>'
                f'<p style="font-family:Arial,sans-serif;font-size:18px;font-weight:bold;color:{color};margin:0;">{value}</p>'
                f'</td>'
            )

        recent = self.get_recent_trades(5)
        trade_rows = ""
        for t in reversed(recent):
            win_color = "#2e7d32" if t["winner"] else "#c62828"
            sign = "+" if t["net_pnl"] >= 0 else ""
            trade_rows += (
                f'<tr>'
                f'<td style="padding:6px 10px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;color:#0d1b2a;border-bottom:1px solid #f5f5f5;">{t["ticker"]}</td>'
                f'<td style="padding:6px 10px;font-family:Arial,sans-serif;font-size:12px;color:#546e7a;border-bottom:1px solid #f5f5f5;">{t["exit_reason"].replace("_"," ")}</td>'
                f'<td style="padding:6px 10px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;color:{win_color};text-align:right;border-bottom:1px solid #f5f5f5;">{sign}${t["net_pnl"]:.2f}</td>'
                f'<td style="padding:6px 10px;font-family:Arial,sans-serif;font-size:12px;color:{win_color};text-align:right;border-bottom:1px solid #f5f5f5;">{sign}{t["pnl_pct"]:.1f}%</td>'
                f'<td style="padding:6px 10px;font-family:Arial,sans-serif;font-size:12px;color:#546e7a;text-align:right;border-bottom:1px solid #f5f5f5;">{t["r_multiple"]:+.2f}R</td>'
                f'</tr>'
            )

        return (
            '<h2 style="font-family:Arial,sans-serif;font-size:13px;color:#78909c;margin:0 0 14px;'
            'text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #e0e0e0;padding-bottom:8px;">'
            'Performance Summary</h2>'
            # Metric grid
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            'style="border-collapse:collapse;border:1px solid #e0e0e0;border-radius:6px;margin-bottom:16px;">'
            '<tr bgcolor="#f5f5f5">'
            + _metric("Total P&L", f'${s["cumulative_pnl"]:+,.2f}', pnl_color)
            + _metric("Total Return", f'{s["total_return_pct"]:+.1f}%', tr_color)
            + _metric("Win Rate", f'{s["win_rate"]:.0f}%')
            + _metric("Trades", str(s["total_trades"]))
            + '</tr><tr>'
            + _metric("Avg Win", f'${s["avg_win"]:.2f}', "#2e7d32")
            + _metric("Avg Loss", f'${s["avg_loss"]:.2f}', "#c62828")
            + _metric("Avg R", f'{s["avg_r_multiple"]:+.2f}R')
            + _metric("Sharpe", f'{s["sharpe_ratio"]:.2f}', sharpe_color)
            + '</tr></table>'
            # Recent trades
            + (
                '<h3 style="font-family:Arial,sans-serif;font-size:12px;color:#78909c;margin:0 0 8px;'
                'text-transform:uppercase;letter-spacing:1px;">Recent Trades</h3>'
                '<table width="100%" cellpadding="0" cellspacing="0" border="0" '
                'style="border-collapse:collapse;border:1px solid #e0e0e0;">'
                '<tr bgcolor="#e8eaf6">'
                '<th style="padding:6px 10px;font-family:Arial,sans-serif;font-size:11px;color:#3949ab;text-align:left;">Ticker</th>'
                '<th style="padding:6px 10px;font-family:Arial,sans-serif;font-size:11px;color:#3949ab;text-align:left;">Exit</th>'
                '<th style="padding:6px 10px;font-family:Arial,sans-serif;font-size:11px;color:#3949ab;text-align:right;">P&amp;L</th>'
                '<th style="padding:6px 10px;font-family:Arial,sans-serif;font-size:11px;color:#3949ab;text-align:right;">%</th>'
                '<th style="padding:6px 10px;font-family:Arial,sans-serif;font-size:11px;color:#3949ab;text-align:right;">R</th>'
                '</tr>'
                + trade_rows
                + '</table>'
                if recent else
                '<p style="font-family:Arial,sans-serif;font-size:13px;color:#78909c;">No trades closed yet.</p>'
            )
        )
