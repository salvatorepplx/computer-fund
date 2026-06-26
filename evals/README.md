# Offline Evals

Run the deterministic, connector-free Computer Fund eval harness:

```sh
python -m evals.run_offline_evals
```

The harness is intentionally small and stdlib-only so it can run locally or in CI without network,
broker access, live market data, account state, or order placement. Current starter evals cover:

- Charter safety rails fail-closed behavior for account allowlist, sizing caps, option premium caps,
  and kill-switch outputs.
- Knowledge graph persistence plus observed-only sentiment behavior so simulated sentiment is never
  treated as observed fact by default.
- Battle discovery deterministic ranking and stable seed-direction behavior from offline fixtures.
- Sentiment simulator determinism, bounded trajectories, predate-window invariants, and projected
  signal labeling.
- Sentiment lead-lag placebo fixtures that accept a true leading signal and reject coincident,
  lagging, random-label, and wrong-universe controls.
- CAP calibration fixture metrics for sentiment peak error, predate timing, edge after explicit
  costs, and conviction-vs-realized-edge readiness.
- KG observed-series replay for `runs/sentiment/series/TICKER_NVDA.jsonl`, using only a temporary
  graph to prove committed observed rows preserve `simulated:false`, timestamp/provenance fields,
  latest observed sentiment, and observed-only momentum.

The observed-series replay is a plumbing diagnostic, not a trading signal. The current NVDA sample is
single-ticker, single-source, and intentionally below the readiness threshold for lead-lag/CAP credit
or meaningful `current_step_est`; it performs no live fetches and never mutates `state/knowledge_graph.json`.

See `evals/falsification_playbook.md` for the tiered sentiment falsification checklist, and
`evals/cap_calibration.md` for the CAP-vs-REG calibration pre-registration.

```sh
env -u PYTHONPATH python -m evals.leadlag_placebo
env -u PYTHONPATH python -m evals.cap_calibration
env -u PYTHONPATH python -m evals.kg_observed_series
```
