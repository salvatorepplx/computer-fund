# Self-Improvement Log

The Fund's running record of how it gets better — across every axis (CONSTITUTION).
Each entry: `[DATE] AXIS — what was wrong / could be better → what changed (or ticket).`

## Open tickets (chip on the shoulder — things that are not good enough yet)

- **[SIM-FIDELITY-1 follow-ups] simulation** — offline diagnostics now measure saturation rate,
  time-to-saturation, peak timing, edge-score distribution, and persistent-network/cascade
  sensitivity. Remaining work is calibration/improvement, not measurement: (a) calibrate against
  *observed* sentiment trajectories from the graph so `edge_score` is meaningful, (b) evaluate
  lead/lag vs CAP outcomes, and (c) improve the diffusion model if diagnostics/evals support it.
  Until calibrated, treat sim output as a weak prior, not a trigger.
- **[GRAPH-SENT-1] knowledge graph** — sentiment is hand-seeded; needs real observed-sentiment
  ingestion (finance ticker sentiment + social proxies) before momentum/`current_step_est` mean anything.
- **[EVAL follow-ups] self-eval** — the starter offline REG harness exists; remaining work is CAP
  eval/calibration coverage and additional falsification suites.
- **[EXEC-SETTLE-1] execution** — cash account is T+1 settlement; sizing logic does not yet model
  unsettled cash. Could over-deploy across same-day round-trips. Add settlement-aware buying power.

## Done

- [2026-06-26] simulation — added offline SIM-FIDELITY-1 diagnostics for saturation rate,
  time-to-saturation, peak timing, edge-score distribution, and persistent-network/cascade
  sensitivity. Current output measures the weakness; it does not yet prove improvement.
- [2026-06-26] self-eval — added EVAL-0 starter offline REG harness at
  `evals/run_offline_evals.py`. This does not yet cover CAP evals or calibration.
- [2026-06-26] engineering — replaced deprecated `datetime.utcnow()` with timezone-aware UTC.
- [2026-06-26] external-systems — Fund versioned in private GitHub repo; can PR against itself.
