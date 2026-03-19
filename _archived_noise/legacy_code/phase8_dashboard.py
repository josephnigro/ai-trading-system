"""
Phase 8 Dashboard (Streamlit)

Launch:
    streamlit run phase8_dashboard.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"
POSITIONS_FILE = LOGS / "positions" / "open_positions.json"
LEDGER_FILE = LOGS / "performance" / "trade_ledger.json"
EQUITY_FILE = LOGS / "performance" / "equity_curve.json"
BACKTEST_DIR = LOGS / "backtests"
NOTIFY_DIR = LOGS / "notifications"
INBOX_DIR = NOTIFY_DIR / "inbox"


def _read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_open_positions() -> List[Dict[str, Any]]:
    raw = _read_json_file(POSITIONS_FILE, {})
    if isinstance(raw, dict):
        return list(raw.values())
    if isinstance(raw, list):
        return raw
    return []


def load_trade_ledger() -> List[Dict[str, Any]]:
    data = _read_json_file(LEDGER_FILE, [])
    return data if isinstance(data, list) else []


def load_equity_curve() -> List[Dict[str, Any]]:
    data = _read_json_file(EQUITY_FILE, [])
    return data if isinstance(data, list) else []


def get_latest_backtest_report() -> Dict[str, Any]:
    if not BACKTEST_DIR.exists():
        return {}
    reports = sorted(BACKTEST_DIR.glob("backtest_report_*.json"))
    if not reports:
        return {}
    return _read_json_file(reports[-1], {})


def get_last_session_log() -> Path | None:
    if not LOGS.exists():
        return None
    sessions = sorted(LOGS.glob("session_*.json"))
    if not sessions:
        return None
    return sessions[-1]


def parse_health() -> Dict[str, Any]:
    last_session = get_last_session_log()
    return {
        "last_session": str(last_session) if last_session else "none",
        "positions_file": POSITIONS_FILE.exists(),
        "ledger_file": LEDGER_FILE.exists(),
        "equity_file": EQUITY_FILE.exists(),
        "notifications_dir": NOTIFY_DIR.exists(),
        "inbox_dir": INBOX_DIR.exists(),
    }


def compute_performance_stats(ledger: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not ledger:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "net_pnl": 0.0,
        }

    pnls = [float(t.get("net_pnl", 0.0)) for t in ledger]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    total = len(pnls)
    return {
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / total) * 100 if total else 0.0,
        "net_pnl": sum(pnls),
    }


def write_approval_response(text: str) -> Path:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = INBOX_DIR / f"dashboard_response_{ts}.txt"
    out.write_text(text.strip() + "\n", encoding="utf-8")
    return out


def render_top_metrics(positions: List[Dict[str, Any]], ledger: List[Dict[str, Any]]) -> None:
    perf = compute_performance_stats(ledger)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Open Positions", len(positions))
    c2.metric("Closed Trades", perf["total_trades"])
    c3.metric("Win Rate", f"{perf['win_rate']:.1f}%")
    c4.metric("Net P&L", f"${perf['net_pnl']:+,.2f}")


def render_positions(positions: List[Dict[str, Any]]) -> None:
    st.subheader("Open Positions")
    if not positions:
        st.info("No open positions in logs/positions/open_positions.json")
        return
    df = pd.DataFrame(positions)
    preferred_cols = [
        "ticker",
        "shares",
        "entry_price",
        "stop_loss",
        "profit_target",
        "opened_at",
        "trade_id",
        "order_id",
    ]
    cols = [c for c in preferred_cols if c in df.columns] + [c for c in df.columns if c not in preferred_cols]
    st.dataframe(df[cols], use_container_width=True)


def render_equity_curve(curve: List[Dict[str, Any]]) -> None:
    st.subheader("Equity Curve")
    if not curve:
        st.info("No equity curve yet. It appears after closed trades are recorded.")
        return
    df = pd.DataFrame(curve)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if "equity" in df.columns:
        chart_df = df.dropna(subset=["timestamp", "equity"]).set_index("timestamp")
        if not chart_df.empty:
            st.line_chart(chart_df["equity"])
    st.dataframe(df.tail(25), use_container_width=True)


def render_closed_trades(ledger: List[Dict[str, Any]]) -> None:
    st.subheader("Closed Trades")
    if not ledger:
        st.info("No closed trades in logs/performance/trade_ledger.json")
        return
    df = pd.DataFrame(ledger)
    st.dataframe(df.tail(50), use_container_width=True)


def render_backtest_summary() -> None:
    st.subheader("Latest Backtest")
    report = get_latest_backtest_report()
    if not report:
        st.info("No backtest report found in logs/backtests")
        return
    summary = report.get("summary", {})
    if not summary:
        st.warning("Backtest file found but no summary block.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trades", summary.get("total_trades", 0))
    c2.metric("Win Rate", f"{summary.get('win_rate_pct', 0):.1f}%")
    c3.metric("Return", f"{summary.get('total_return_pct', 0):+.2f}%")
    c4.metric("Sharpe", f"{summary.get('sharpe_ratio', 0):.2f}")

    st.json(summary)


def render_approval_panel() -> None:
    st.subheader("Trade Approval")
    st.caption("Writes approval files directly to logs/notifications/inbox")

    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("Approve All", use_container_width=True):
        path = write_approval_response("yes")
        st.success(f"Wrote: {path}")
    if c2.button("Reject All", use_container_width=True):
        path = write_approval_response("no")
        st.success(f"Wrote: {path}")

    response_text = c3.text_input(
        "Custom response",
        value="1,3",
        help="Examples: yes, no, 1,3, PLTR,GME",
    )
    if st.button("Submit Custom Response", use_container_width=True):
        path = write_approval_response(response_text)
        st.success(f"Wrote: {path}")


def render_health_panel() -> None:
    st.subheader("System Health")
    h = parse_health()
    st.write(h)


def main() -> None:
    st.set_page_config(page_title="AI Trading Scanner Dashboard", layout="wide")
    st.title("AI Trading Scanner — Phase 8 Dashboard")
    st.caption("Live ops view for positions, performance, backtests, and approvals")

    positions = load_open_positions()
    ledger = load_trade_ledger()
    curve = load_equity_curve()

    render_top_metrics(positions, ledger)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Positions", "Performance", "Backtests", "Approvals", "Health"]
    )

    with tab1:
        render_positions(positions)
    with tab2:
        render_equity_curve(curve)
        render_closed_trades(ledger)
    with tab3:
        render_backtest_summary()
    with tab4:
        render_approval_panel()
    with tab5:
        render_health_panel()


if __name__ == "__main__":
    main()
