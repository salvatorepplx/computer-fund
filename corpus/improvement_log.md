# Computer Fund — Improvement Log

This log is the durable backlog for recursive self-improvement. Keep entries small, falsifiable, and tied to reviewable artifacts.

## Status legend

- `OPEN` — accepted backlog item, not yet implemented.
- `IN_PROGRESS` — active work has started.
- `DONE` — merged or otherwise accepted by Computer/Sal.
- `BLOCKED` — waiting on explicit human input or missing external access.

## Entries

### SIM-FIDELITY-1 — Measure and reduce sentiment-sim saturation

- **Status:** `OPEN`
- **Axis:** Simulation fidelity
- **Problem:** The sentiment simulation is reported to saturate too fast and produce weak edge. A sim that rapidly collapses to extreme sentiment can look decisive while failing to predict observed sentiment.
- **Why it matters:** Saturation can hide uncertainty, overstate conviction, and feed brittle alpha rankings.
- **Safety constraints:** No look-ahead. Every observed signal must be timestamped. Every simulated signal must be labeled as simulated and must never be presented as fact.
- **Starting evidence:** Slack handoff identifies this as the first simulation-fidelity gap. The current repo has no `sim/` module yet, so the first worker should make the failure measurable before changing strategy behavior.
- **Suggested next artifact:** A minimal `sim/` fixture and metric report that tracks saturation rate, time-to-saturation, calibration against later observed sentiment, and sensitivity to seed assumptions.
- **Acceptance sketch:** A local command or eval can reproduce the saturation metric on deterministic fixtures, and any proposed improvement reports before/after behavior without live data access.

### EVAL-0 — Add a minimal eval harness

- **Status:** `OPEN`
- **Axis:** Self-evaluation
- **Problem:** The repo has safety code and a knowledge graph, but no eval harness to prevent regressions or encode Fund-specific invariants.
- **Why it matters:** The Fund cannot recursively self-improve safely without tests that catch violations of the Charter, fabricated signals, look-ahead leakage, or broken graph behavior.
- **Safety constraints:** Evals must not place trades, touch Robinhood, access live market data, or require human credentials. Trading-adjacent evals should exercise proposals and review artifacts only.
- **Starting evidence:** Slack handoff identifies no eval harness yet. Current code includes `execution/safety.py` and `graph/kg.py`, which are natural first targets for local evals.
- **Suggested next artifact:** A lightweight `evals/` or test harness that validates safety-rail failures, allowed proposal review behavior, knowledge-graph persistence, timestamp handling, and explicit labeling of simulated sentiment.
- **Acceptance sketch:** A documented local command runs deterministic evals in CI-friendly mode and fails closed on safety/no-look-ahead regressions.
