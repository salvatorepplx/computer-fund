# CAP Calibration Evals

The offline eval harness has two layers:

- **REG evals** are regression/safety checks that must stay at 100%. They protect Charter rails such as account allowlists, sizing caps, kill-switch behavior, observed-vs-simulated sentiment separation, deterministic ranking, and falsifier invariants.
- **CAP evals** are capability checks that should improve as the research/simulation loop gets better. They measure whether the Fund's sentiment simulations predicted and predated later observed outcomes, without weakening REG gates.

This scaffold is deliberately offline and pre-registered. It does not fetch broker data, live market data, account state, order state, or produce execution advice.

## Pre-Registered Row Schema

Each future observed-history row must be written explicitly before scoring:

```json
{
  "thesis_id": "stable unique thesis or ticket id",
  "projected_peak_step": 5,
  "observed_peak_step": 6,
  "projected_peak_sentiment": 0.46,
  "observed_peak_sentiment": 0.43,
  "entry_step": 2,
  "expected_edge": 0.06,
  "realized_return": 0.05,
  "benchmark_return": 0.02,
  "round_trip_cost": 0.006,
  "conviction": 0.82,
  "closed": true
}
```

Step units are the pre-registered cadence for the thesis, such as heartbeat ticks or observation windows. Sentiment values use the simulator/graph convention of `-1.0` to `+1.0`. Returns and costs are decimal fractions of capital at risk for that thesis, not account-level P&L.

## Metrics

- `sentiment_peak_error`: absolute distance between projected and later observed peak sentiment. Lower is better.
- `predate_timing_steps`: `observed_peak_step - entry_step`. Positive means the entry predated the observed sentiment peak; zero or negative means coincident/late; missing means no entry was made.
- `edge_after_costs`: `realized_return - benchmark_return - round_trip_cost`. Positive means the closed thesis beat the benchmark after explicit costs.
- `conviction_edge_after_costs_pearson`: Pearson correlation between pre-trade conviction and realized edge after costs. This remains `null` until at least 10 closed positions with conviction exist.

## Calibration Rules

- Do not tune thresholds on rows being scored. Threshold changes require a new dated calibration note and should only use rows that were closed before the change was proposed.
- Do not backfill missing observed fields from simulator output. If a row lacks observed sentiment, benchmark return, costs, or closure state, exclude it until those fields are explicitly recorded.
- Report CAP movement separately from REG status. CAP can be low or noisy while REG still passes; REG failures block trust in any CAP improvement.
- Treat the first 10 closed rows as calibration warm-up. Before `N >= 10`, conviction thresholds remain provisional and the tracker only reports sample counts plus non-calibration metrics.
- Preserve killed or no-entry theses. `closed=false` rows still contribute to sentiment/timing diagnostics when observed fields exist, but not to conviction-vs-P&L calibration.

## Commands

```sh
env -u PYTHONPATH python -m evals.cap_calibration
env -u PYTHONPATH python -m evals.run_offline_evals
```
