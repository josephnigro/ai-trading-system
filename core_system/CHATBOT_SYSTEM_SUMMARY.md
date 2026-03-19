# AI Trading Scanner - System Handoff Summary

Date: 2026-03-18
Scope: Active execution system under `core_system/`

## 1) What this system does

This is a modular stock-trading scanner pipeline that:

1. pulls market data (OHLCV + quote) from Yahoo Finance,
2. computes multi-model trading signals,
3. applies risk and quality filters,
4. creates trade proposals for user approval,
5. optionally executes approved trades via Alpaca,
6. logs everything for auditability,
7. monitors open positions for stop/target alerts.

It is designed as a "human-in-the-loop" workflow: scan first, approve/reject, then optional execution.

## 2) Core architecture and how it connects

Primary orchestrator:
- `orchestrator.py` -> `TradingOrchestrator`

Connected modules:
- Data: `src/data_module/yfinance_provider.py`
- Signals: `src/signal_engine/signal_generator.py`
- Risk: `src/risk_management/risk_manager.py`
- Scoring/Proposal: `src/scoring_engine/scoring_engine.py`
- Execution: `src/execution_module/execution_engine.py`
- Notifications: `src/notification_module/notification_engine.py`
- Logging: `src/logging_module/logging_engine.py`
- Position persistence/monitoring:
  - `src/position_monitor/position_store.py`
  - `src/position_monitor/position_monitor.py`

High-level flow:

1. `initialize()` initializes each module and sets ticker universe.
2. `run_scan()` loops through universe and for each ticker:
   - fetches OHLCV + quote,
   - generates a signal,
   - applies pre-proposal quality score filter,
   - creates a proposal via scoring + risk checks.
3. `send_daily_proposal_digest()` sends/prints digest.
4. `process_user_approval_response()` maps yes/no/list/ticker approvals.
5. `execute_approved_trades()` executes via broker and stores open positions.
6. `PositionMonitor` later checks stops/targets and can auto-close.

## 3) Current feature set

Implemented features:

- Multi-factor signal generation:
  - technical analysis (RSI, MACD, MA trend),
  - momentum-style ML heuristic,
  - sentiment-style volume/momentum logic.
- Signal gating:
  - buy when `avg_score > 1.0`,
  - sell when `avg_score < -1.0`.
- Proposal quality gate before scoring:
  - 4-point quality score using price, average volume, market cap, and volume spike,
  - minimum required quality score: 3.
- Risk controls:
  - risk per trade,
  - max position percentage,
  - max daily risk,
  - max concurrent positions,
  - configurable target/stop percentages.
- Human approval loop:
  - supports yes/no/all,
  - supports index/ticker-based selective approvals.
- Execution support:
  - broker abstraction with Alpaca implementation path.
- Notifications:
  - text digest,
  - rich HTML digest,
  - SMTP and Twilio transport readiness checks,
  - inbox response ingestion from file.
- Audit and persistence:
  - session event logs,
  - trade/proposal/execution records,
  - open positions JSON store for monitoring.

## 4) Strengths

- Clear modular design with separable concerns.
- Good operational observability: logging, digesting, approval parsing.
- Safety layering: signal thresholding + quality filtering + risk checks.
- Human approval step reduces accidental auto-trading risk.
- Degraded data handling is generally resilient (failed symbols usually skipped, not fatal).
- Execution is optional, so scanner mode can run without broker credentials.

## 5) Weaknesses / risks

- Data source limitations:
  - Yahoo Finance may be slow, unstable, or missing data for delisted tickers.
- Universe quality:
  - default universe contains several degraded/delisted symbols that create noisy errors.
- Performance profile:
  - scan loop is synchronous ticker-by-ticker (no batching/async), so throughput is limited.
- Strategy sophistication:
  - "ML predictor" is momentum heuristic, not a trained model lifecycle.
- Validation/test depth:
  - code is modular, but production-grade test coverage and CI guardrails are not obvious in the core path.
- Market microstructure realism:
  - no explicit slippage/spread/latency modeling in proposal scoring.
- Portfolio management depth:
  - lacks portfolio-level optimization and correlation-aware position sizing.

## 6) Features it still needs (priority list)

High priority:

1. Replace/augment yfinance with a more robust market data provider and fallback routing.
2. Clean and maintain stock universe (remove stale symbols automatically).
3. Add async/batched data retrieval to cut scan time.
4. Add deterministic integration tests around orchestrator happy-path and failure-path.

Medium priority:

1. Add portfolio-level constraints (sector/correlation/exposure caps).
2. Add structured retry policy + circuit breakers for external API failures.
3. Add richer execution simulation (slippage, partial fills, fees).
4. Add confidence calibration and post-trade model feedback loop.

Nice to have:

1. Dashboard-level explainability views for each trade score component.
2. Auto-pruning archival/log retention controls.
3. Multi-broker execution adapters.

## 7) What is left to finish

The framework is functionally complete for a scan -> approve -> optional execute workflow.
Most remaining work is production hardening, not greenfield architecture:

- data reliability hardening,
- test automation expansion,
- performance optimization,
- more realistic execution/portfolio controls,
- stronger operational safeguards for live deployment.

## 8) Is it working efficiently?

Short answer: functionally yes, computationally moderate.

- It works end-to-end and degrades safely on many bad symbols.
- Main efficiency bottleneck is serial data pulling + repeated remote requests per ticker.
- Quality filter and thresholds reduce low-value proposals, improving downstream efficiency.
- For larger universes or intraday cadence, async/batch processing is needed.

## 9) Latest runtime status snapshot (2026-03-18)

Observed in current environment:

- Orchestrator initialization succeeded (`INIT_OK=True`).
- Scan cycle completed (`SCAN_COMPLETED=1`) without a process crash.
- Proposal generation returned non-zero opportunities in recent run(s).
- Some symbols still report "possibly delisted" from yfinance; these are skipped and do not stop the run.

Interpretation:
- core system is operational,
- scanner is resilient to partial data failures,
- reliability/efficiency improvements should focus on data source quality and scan parallelization.

## 10) One-paragraph chatbot-ready summary

This project is a modular AI-assisted trading scanner that runs a full pipeline: market data ingestion, multi-factor signal generation, risk-aware proposal scoring, user approval parsing, optional broker execution, and position monitoring with notifications. It is architecturally strong and operationally usable now, with clear module boundaries and audit logging, and it currently initializes and scans successfully without crashing. Its main weaknesses are data-source fragility (yfinance/delisted tickers), synchronous scan performance, and limited production hardening (testing, portfolio-level controls, execution realism). The system is best viewed as a working core engine that now needs reliability, speed, and institutional risk features to be production-grade.
