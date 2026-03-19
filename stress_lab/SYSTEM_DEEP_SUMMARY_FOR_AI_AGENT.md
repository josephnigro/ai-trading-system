# AI Trading Scanner - Deep System Summary for AI Agent

Generated: 2026-03-19 UTC
Scope: Current workspace state, with focus on active runtime in `core_system` plus standalone stress tooling in `stress_lab`.
Tone: Practical, candid, and implementation-specific.

## 1) What this app is, in plain English

This is a modular trading workflow engine designed to scan a stock universe, generate risk-aware trade ideas, ask for user approval, optionally execute approved trades through Alpaca, and keep a full audit trail with notifications.

The app is not a "fully autonomous hedge fund bot." It is a disciplined human-in-the-loop system:

1. Scan market data.
2. Generate candidate trades.
3. Filter and size them with risk constraints.
4. Ask for approval.
5. Execute only approved setups.
6. Monitor open positions.

That design choice is intentional and is the core ethos of the project.

## 2) Application ethos (why it is built this way)

The system favors controllability and survivability over raw aggressiveness:

- Modularity over monolith: each domain has a dedicated module.
- Guardrails before action: quality filter + risk manager + approval path.
- Graceful degradation: data provider failures should skip/fallback, not crash.
- Auditability: every major action is logged and reviewable.
- Real-world pragmatism: paper/live Alpaca capability, digest notifications, and stress instrumentation.

In short: this project is trying to be a resilient operations system, not just a strategy script.

## 3) What it is currently connected to

### Live external integrations

- Polygon.io (primary data attempt): configured by API key env vars.
- Yahoo Finance (fallback data source): used when Polygon fails or is restricted.
- Alpaca (execution/broker): connected in paper mode capability.
- SMTP email: configured and verified for outbound messages.

### Current verified readiness snapshot

From latest diagnostics:

- `POLYGON_KEY` present: true
- `ALPACA_KEY` present: true
- `ALPACA_SECRET` present: true
- `SMTP_ENABLED` configured: true
- `SMTP host/user/pass/from/to` present: true
- Alpaca account call succeeded in paper mode in recent check.
- Direct SMTP test email succeeded (`EMAIL_SENT=1` in recent run).

## 4) End-to-end flow (actual code path)

Primary orchestrator lives in `core_system/orchestrator.py`.

High-level runtime sequence:

1. `TradingOrchestrator.initialize()` initializes all modules.
2. `run_scan()` loops tickers:
   - `DataModule.get_ohlcv()` and `DataModule.get_quote()`
   - `SignalEngine.generate_signal()`
   - pre-proposal quality score filter
   - `ScoringEngine.create_proposal()` with risk constraints
3. `send_daily_proposal_digest()` renders/sends digest.
4. `process_user_approval_response()` parses human response.
5. `execute_approved_trades()` sends orders through `ExecutionModule` + Alpaca.
6. Position persistence/monitoring handles stop/target tracking.
7. `shutdown()` writes logs and closes module lifecycle cleanly.

## 5) Data layer behavior (important)

Data provider is `PolygonFallbackDataProvider` in `core_system/src/data_module/polygon_provider.py`.

Behavior:

1. Tries Polygon first.
2. Falls back to yfinance if Polygon fails.
3. Returns OHLCV in expected DataFrame shape (`Open`, `High`, `Low`, `Close`, `Volume`).
4. Returns quote dict with market cap defaulting to `0` when unavailable.
5. Includes a circuit-breaker cooldown for repeated `429` / `403` responses to avoid API hammering.

This means the system keeps running even when Polygon is rate-limited or denied for a specific endpoint.

## 6) Full file map and purpose (active system)

## Core top-level runtime files

- `core_system/orchestrator.py`: Main workflow coordinator and execution control plane.
- `core_system/EXECUTION_RULE.txt`: Declares `/core_system` as active runtime boundary.
- `core_system/CHATBOT_SYSTEM_SUMMARY.md`: Prior high-level summary artifact.
- `core_system/stress_drill.py`: earlier ad-hoc drill script.
- `core_system/auto_real_drill_runner.py`: readiness watcher + auto-run trigger for real drills.
- `core_system/MOVED_REQUIRED_FILES.txt`: relocation manifest from repo organization pass.

## Core source modules (`core_system/src`)

### Broker

- `src/broker/alpaca_broker.py`: Alpaca adapter (paper/live modes, order placement, account/position queries).
- `src/broker/__init__.py`: broker package export stub.

### Core abstractions and models

- `src/core/base_module.py`: base lifecycle + logging contract for modules.
- `src/core/data_interface.py`: provider interface + DataModule wrapper and convenience retrieval.
- `src/core/signal.py`: signal model/type structure.
- `src/core/trade_proposal.py`: proposal model, statuses, approval lifecycle.
- `src/core/execution_record.py`: execution model and trade lifecycle record.
- `src/core/__init__.py`: core package exports.

### Data

- `src/data_module/yfinance_provider.py`: Yahoo data provider implementation.
- `src/data_module/polygon_provider.py`: Polygon-first fallback provider.
- `src/data_module/__init__.py`: data module exports and provider wiring.

### Signal generation

- `src/signal_engine/signal_generator.py`: technical + momentum + sentiment scoring and signal thresholds.
- `src/signal_engine/__init__.py`: signal package exports.

### Proposal scoring

- `src/scoring_engine/scoring_engine.py`: confidence/risk checks, position sizing integration, proposal creation.
- `src/scoring_engine/__init__.py`: scoring package exports.

### Risk

- `src/risk_management/risk_manager.py`: limits, risk math, targets/stops, exposure tracking.
- `src/risk_management/__init__.py`: risk package exports.

### Execution

- `src/execution_module/execution_engine.py`: broker integration interface + execution orchestration.
- `src/execution_module/__init__.py`: execution package exports.

### Logging and notifications

- `src/logging_module/logging_engine.py`: session/event logging and persistence.
- `src/logging_module/__init__.py`: logging package exports.
- `src/notification_module/notification_engine.py`: digest rendering (text/HTML), SMTP/Twilio transport, response ingestion.
- `src/notification_module/__init__.py`: notification package exports.

### Position monitoring

- `src/position_monitor/position_store.py`: JSON-backed open-position persistence.
- `src/position_monitor/position_monitor.py`: stop/target monitoring and alert/close logic.
- `src/position_monitor/__init__.py`: position package exports.

## Standalone stress-lab files (not part of core runtime)

- `stress_lab/run_stress_lab.py`: standalone stress runner that appends test history and generates feedback report.
- `stress_lab/stress_test_history.jsonl`: append-only historical run database.
- `stress_lab/latest_stress_feedback.md`: latest run feedback summary.
- `stress_lab/latest_stress_feedback.docx`: handoff-ready Word version of latest report.
- `stress_lab/README.md`: stress lab scope and file intent.

## 7) Diagnostics and health breakdown

## Static/code diagnostics

- Core source files under `core_system` currently show no editor problems in latest check.
- Core source file count: 22 Python files under `core_system/src`.

Largest modules by byte size (good proxy for complexity concentration):

1. `core_system/src/notification_module/notification_engine.py` (~50 KB)
2. `core_system/src/position_monitor/position_monitor.py`
3. `core_system/src/signal_engine/signal_generator.py`
4. `core_system/src/broker/alpaca_broker.py`
5. `core_system/src/data_module/polygon_provider.py`

Interpretation: notification/rendering + signal logic + broker/data connectors are the main complexity hotspots.

## Stress-lab runtime metrics (history-backed)

Historical records currently in stress DB: 5 entries.

Aggregates observed:

- Total proposals: 0
- Total executions: 0
- Email test success rate: 100%
- Latest bounded run average iteration duration: ~4.93s

Interpretation:

- Plumbing and operational paths are stable.
- Strategy output is currently too restrictive or market-window-unfavorable (no proposals), so execution path is not naturally exercised.

## Integration behavior observed during stress

- Polygon key is present, but some Polygon snapshot/aggregate endpoints returned `403` or `429` during test windows.
- Fallback to yfinance preserved runtime continuity and prevented crash.
- SMTP transport successfully sent test emails.
- Alpaca broker readiness and account access in paper mode were validated.

## 8) Strengths

1. Strong module separation and clear domain boundaries.
2. Stable lifecycle management (`initialize`/`shutdown`) with logging hooks.
3. Data-layer fallback strategy prevents brittle failures.
4. Human approval gate reduces unintended live execution risk.
5. Stress-lab instrumentation now captures historical run behavior.
6. Operational integrations (SMTP, Alpaca paper connectivity) are proven reachable.

## 9) Weaknesses and risk areas

1. Proposal generation hit-rate currently low (zero in recent stress windows).
2. Polygon free-tier constraints can reduce primary-data reliability for broad scans.
3. Execution path validation depends on receiving proposals; currently under-exercised in normal drill runs.
4. Notification module has high complexity concentration (largest file), increasing maintenance burden.
5. Existing stress reports track outcomes but not yet rich root-cause counters (e.g., per-ticker source success/fallback stats).

## 10) What works today vs what is missing

## Works now

- Initialization, scanning loop, and digest generation are stable.
- Email transport works.
- Alpaca account connectivity works (paper mode).
- Data fallback works when Polygon endpoints fail.
- Standalone stress history/feedback loop is in place.

## Missing / not yet validated at depth

- Consistent generation of qualified proposals in the current market/test universe.
- Repeatable trade execution events from strategy-driven approvals.
- Fine-grained attribution metrics: exactly how often each ticker uses Polygon vs fallback and why.

## 11) Clear improvement roadmap for next AI agent

Priority 1 (high impact, low architectural disruption):

1. Add per-iteration and per-ticker data-source counters in stress output.
2. Add explicit reason taxonomy for proposal rejection (confidence, risk/reward, quality gate, etc.).
3. Add a standalone paper-order smoke test mode in stress lab to validate execution plumbing independent of strategy output.

Priority 2:

1. Tune scanner universe selection for stress windows to improve proposal coverage.
2. Add adaptive scan-size logic when repeated Polygon `429` is detected.
3. Split large notification module into renderer + transport + parser subcomponents.

Priority 3:

1. Build longitudinal dashboard from `stress_test_history.jsonl`.
2. Add regression thresholds (latency, email success, proposal floor) and fail-fast alerts.

## 12) Bottom-line verdict

This application is not broken. It is operationally coherent and technically organized, with real integrations and a survivable fallback strategy.

The current bottleneck is not infrastructure readiness; it is strategy output frequency under present thresholds/data conditions.

If the goal is immediate higher trade activity, the next wave should focus on measurable proposal-generation diagnostics and controlled threshold/universe experiments, while keeping the existing safety/approval ethos intact.
