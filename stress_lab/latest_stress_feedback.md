# Stress Test Feedback Loop Report

Generated UTC: 2026-03-19T01:15:39.362958+00:00

## Scope

Standalone stress-lab run only. No integration into core runtime flow.

## Summary Metrics

- Iterations: 2
- Init success: 2/2
- Cycle success: 2/2
- Email test sends: 2/2
- Broker ready checks: 2/2
- SMTP ready checks: 2/2
- Total proposals: 0
- Total executions: 0
- Avg iteration duration (s): 4.93

## What Worked

- Initialization stable across all stress iterations.
- SMTP email transport is sending test messages.
- Alpaca broker credentials and SDK path are available.
- SMTP readiness stayed configured throughout the test.

## What Is Missing / Failed

- No qualified proposals were generated in this window.
- No trades executed (no approved proposals to execute).

## Improvement Backlog

- Track a broader/different ticker universe for test windows to increase proposal hit-rate.
- Add a dedicated paper-trade smoke mode that executes one fixed-symbol micro-order for connectivity checks.
- Store run metadata in JSONL (already enabled) and review weekly trends.
- Add per-iteration API-source counters (Polygon success/fallback counts) to quantify data-layer reliability.
- Set alert thresholds for repeated 429/403 responses to trigger adaptive scan-size reductions.

## Raw Iteration Data (This Run)

```json
[
  {
    "iteration": 1,
    "timestamp_utc": "2026-03-19T01:15:29.506974+00:00",
    "init_ok": true,
    "cycle_ok": true,
    "proposals": 0,
    "executions": 0,
    "response_received": false,
    "email_test_sent": true,
    "broker_ready": true,
    "smtp_ready": true,
    "error": "",
    "duration_seconds": 4.73
  },
  {
    "iteration": 2,
    "timestamp_utc": "2026-03-19T01:15:34.237942+00:00",
    "init_ok": true,
    "cycle_ok": true,
    "proposals": 0,
    "executions": 0,
    "response_received": false,
    "email_test_sent": true,
    "broker_ready": true,
    "smtp_ready": true,
    "error": "",
    "duration_seconds": 5.12
  }
]
```