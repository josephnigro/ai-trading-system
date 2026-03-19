"""
Backtest Engine — Phase 7

Runs a historical walk-forward backtest using the existing signal engine and
risk model assumptions.

Design:
- Fetch full daily OHLCV history for each ticker
- Walk day by day and generate a signal using data available up to that day
- Simulate trade outcomes by checking future candles for stop/target hits
- Record every trade and compute portfolio-level statistics
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import json
import math

import pandas as pd
import yfinance as yf

from ..signal_engine import SignalEngine


@dataclass
class BacktestConfig:
    tickers: List[str]
    start_date: str
    end_date: str
    initial_equity: float = 100000.0
    risk_per_trade_pct: float = 1.0
    max_hold_days: int = 10
    min_confidence: float = 55.0
    min_history_bars: int = 60
    out_dir: str = "logs/backtests"


class BacktestEngine:
    """Historical backtesting engine."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.signal_engine = SignalEngine()
        self.signal_engine.initialize()
        self.out_dir = Path(config.out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _fetch_history(self, ticker: str) -> pd.DataFrame:
        data = yf.download(
            ticker,
            start=self.config.start_date,
            end=self.config.end_date,
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        if data is None or data.empty:
            return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            # yfinance can return (field, ticker) columns; collapse to field names.
            data.columns = data.columns.get_level_values(0)
        return data.dropna(subset=["Open", "High", "Low", "Close", "Volume"])  # type: ignore[arg-type]

    def _position_size(self, equity: float, entry: float, stop: float) -> int:
        risk_dollars = equity * (self.config.risk_per_trade_pct / 100.0)
        risk_per_share = abs(entry - stop)
        if risk_per_share <= 0 or entry <= 0:
            return 0
        shares_by_risk = int(risk_dollars / risk_per_share)
        shares_by_cash = int(equity / entry)
        return max(0, min(shares_by_risk, shares_by_cash))

    def _simulate_exit(
        self,
        data: pd.DataFrame,
        entry_idx: int,
        entry_price: float,
        stop: float,
        target: float,
    ) -> Dict[str, Any]:
        end_idx = min(len(data) - 1, entry_idx + self.config.max_hold_days)
        for idx in range(entry_idx + 1, end_idx + 1):
            candle = data.iloc[idx]
            low = float(candle["Low"])
            high = float(candle["High"])
            if low <= stop:
                return {
                    "exit_idx": idx,
                    "exit_price": stop,
                    "exit_reason": "stop_hit",
                }
            if high >= target:
                return {
                    "exit_idx": idx,
                    "exit_price": target,
                    "exit_reason": "target_hit",
                }

        # Time stop: close at final candle close in window
        final_idx = end_idx
        return {
            "exit_idx": final_idx,
            "exit_price": float(data.iloc[final_idx]["Close"]),
            "exit_reason": "time_stop",
        }

    def run(self) -> Dict[str, Any]:
        trades: List[Dict[str, Any]] = []
        equity_curve: List[Dict[str, Any]] = []
        equity = self.config.initial_equity

        for ticker in self.config.tickers:
            df = self._fetch_history(ticker)
            if len(df) < self.config.min_history_bars + self.config.max_hold_days + 2:
                continue

            i = self.config.min_history_bars
            while i < len(df) - self.config.max_hold_days - 1:
                window = df.iloc[: i + 1]
                current_price = float(window.iloc[-1]["Close"])
                signal = self.signal_engine.generate_signal(ticker, window, current_price)
                if signal is None:
                    i += 1
                    continue

                # Backtest only long entries for now
                if signal.signal_type.value != "BUY":
                    i += 1
                    continue

                if signal.overall_confidence < self.config.min_confidence:
                    i += 1
                    continue

                entry = float(signal.entry_price)
                stop = float(signal.stop_loss)
                target = float(signal.profit_target)
                shares = self._position_size(equity, entry, stop)
                if shares <= 0:
                    i += 1
                    continue

                sim = self._simulate_exit(df, i, entry, stop, target)
                exit_idx = int(sim["exit_idx"])
                exit_price = float(sim["exit_price"])
                exit_reason = str(sim["exit_reason"])

                pnl = (exit_price - entry) * shares
                cost_basis = entry * shares
                pnl_pct = (pnl / cost_basis) * 100 if cost_basis > 0 else 0.0
                risk_per_share = abs(entry - stop)
                r_multiple = (pnl / (risk_per_share * shares)) if risk_per_share > 0 else 0.0

                opened_at = window.index[-1]
                closed_at = df.index[exit_idx]
                hold_days = (closed_at - opened_at).days if hasattr(closed_at, "__sub__") else 0

                equity += pnl

                trade = {
                    "ticker": ticker,
                    "opened_at": str(opened_at),
                    "closed_at": str(closed_at),
                    "hold_days": hold_days,
                    "entry_price": round(entry, 4),
                    "exit_price": round(exit_price, 4),
                    "stop_loss": round(stop, 4),
                    "profit_target": round(target, 4),
                    "shares": shares,
                    "confidence": round(float(signal.overall_confidence), 2),
                    "exit_reason": exit_reason,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "r_multiple": round(r_multiple, 3),
                    "winner": pnl > 0,
                    "equity_after": round(equity, 2),
                }
                trades.append(trade)
                equity_curve.append({
                    "timestamp": trade["closed_at"],
                    "equity": trade["equity_after"],
                    "trade_number": len(trades),
                })

                # Move forward to exit day to avoid overlapping same-ticker trades
                i = exit_idx + 1

        summary = self._build_summary(trades)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report = {
            "config": {
                "tickers": self.config.tickers,
                "start_date": self.config.start_date,
                "end_date": self.config.end_date,
                "initial_equity": self.config.initial_equity,
                "risk_per_trade_pct": self.config.risk_per_trade_pct,
                "max_hold_days": self.config.max_hold_days,
                "min_confidence": self.config.min_confidence,
            },
            "summary": summary,
            "trades": trades,
            "equity_curve": equity_curve,
        }

        json_path = self.out_dir / f"backtest_report_{timestamp}.json"
        csv_path = self.out_dir / f"backtest_trades_{timestamp}.csv"

        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        pd.DataFrame(trades).to_csv(csv_path, index=False)

        report["artifacts"] = {
            "report_json": str(json_path),
            "trades_csv": str(csv_path),
        }
        return report

    def _build_summary(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not trades:
            return {
                "total_trades": 0,
                "winners": 0,
                "losers": 0,
                "win_rate_pct": 0.0,
                "cumulative_pnl": 0.0,
                "avg_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "avg_r_multiple": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "ending_equity": self.config.initial_equity,
                "total_return_pct": 0.0,
            }

        pnls = [float(t["pnl"]) for t in trades]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p <= 0]
        total = len(trades)
        win_rate = (len(winners) / total) * 100.0

        cumulative_pnl = sum(pnls)
        avg_pnl = cumulative_pnl / total
        avg_win = (sum(winners) / len(winners)) if winners else 0.0
        avg_loss = (sum(losers) / len(losers)) if losers else 0.0
        profit_factor = abs(sum(winners) / sum(losers)) if losers and sum(losers) != 0 else 0.0
        avg_r = sum(float(t["r_multiple"]) for t in trades) / total

        # Max drawdown on equity trajectory
        equity = self.config.initial_equity
        peak = equity
        max_dd = 0.0
        for p in pnls:
            equity += p
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        # Sharpe approximation on trade returns
        returns = [p / self.config.initial_equity for p in pnls]
        if len(returns) >= 2:
            mean_r = sum(returns) / len(returns)
            variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
            std_r = math.sqrt(variance)
            sharpe = (mean_r / std_r) * math.sqrt(252) if std_r > 0 else 0.0
        else:
            sharpe = 0.0

        ending_equity = self.config.initial_equity + cumulative_pnl
        total_return = (cumulative_pnl / self.config.initial_equity) * 100.0

        return {
            "total_trades": total,
            "winners": len(winners),
            "losers": len(losers),
            "win_rate_pct": round(win_rate, 2),
            "cumulative_pnl": round(cumulative_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 3),
            "avg_r_multiple": round(avg_r, 3),
            "max_drawdown_pct": round(max_dd * 100.0, 3),
            "sharpe_ratio": round(sharpe, 3),
            "ending_equity": round(ending_equity, 2),
            "total_return_pct": round(total_return, 3),
        }
