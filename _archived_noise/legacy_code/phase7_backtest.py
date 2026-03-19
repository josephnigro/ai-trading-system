"""Phase 7 backtesting runner."""

import argparse
import json
from dotenv import load_dotenv

from src.backtesting import BacktestConfig, BacktestEngine


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 7 Backtesting Runner")
    parser.add_argument(
        "--tickers",
        type=str,
        default="PLTR,SOFI,GME,AMC,NIO",
        help="Comma-separated ticker list",
    )
    parser.add_argument("--start", type=str, default="2024-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, default="2026-03-18", help="End date YYYY-MM-DD")
    parser.add_argument("--initial-equity", type=float, default=100000.0)
    parser.add_argument("--risk-pct", type=float, default=1.0)
    parser.add_argument("--max-hold-days", type=int, default=10)
    parser.add_argument("--min-confidence", type=float, default=55.0)
    parser.add_argument("--min-history-bars", type=int, default=60)
    parser.add_argument("--out-dir", type=str, default="logs/backtests")
    return parser


def main() -> None:
    load_dotenv()
    args = _parser().parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    cfg = BacktestConfig(
        tickers=tickers,
        start_date=args.start,
        end_date=args.end,
        initial_equity=args.initial_equity,
        risk_per_trade_pct=args.risk_pct,
        max_hold_days=args.max_hold_days,
        min_confidence=args.min_confidence,
        min_history_bars=args.min_history_bars,
        out_dir=args.out_dir,
    )

    report = BacktestEngine(cfg).run()
    summary = report["summary"]

    print("\n" + "=" * 72)
    print("PHASE 7 BACKTEST COMPLETE")
    print("=" * 72)
    print(json.dumps(summary, indent=2))
    print("Artifacts:")
    print(f"  JSON: {report['artifacts']['report_json']}")
    print(f"  CSV:  {report['artifacts']['trades_csv']}")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
