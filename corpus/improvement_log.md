# Self-Improvement Log

The Fund's running record of how it gets better — across every axis (CONSTITUTION).
Each entry: `[DATE] AXIS — what was wrong / could be better → what changed (or ticket).`

## Open tickets (chip on the shoulder — things that are not good enough yet)

- **[SIM-FIDELITY-1] simulation** — the v0 diffusion model saturates too fast and produces a
  weak edge (~0.05) with the peak landing past where observed sentiment sits, so `predate_signal`
  fires `act:false` even on a strong seed. The model needs: (a) stronger influencer cascades,
  (b) a real (persistent) network instead of per-step resampling, (c) calibration against
  *observed* sentiment trajectories from the graph so `edge_score` is meaningful. Until calibrated,
  treat sim output as a weak prior, not a trigger.
- **[GRAPH-SENT-1] knowledge graph** — sentiment is hand-seeded; needs real observed-sentiment
  ingestion (finance ticker sentiment + social proxies) before momentum/`current_step_est` mean anything.
- **[EVAL-0] self-eval** — no eval harness yet; cannot yet measure whether the loop is improving.
  Highest-leverage next infra after the loop runs once.
- **[EXEC-SETTLE-1] execution** — cash account is T+1 settlement; sizing logic does not yet model
  unsettled cash. Could over-deploy across same-day round-trips. Add settlement-aware buying power.

## Done

- [2026-06-26] simulation — added offline SIM-FIDELITY-1 diagnostics for saturation rate,
  time-to-saturation, peak timing, edge-score distribution, and persistent-network/cascade
  sensitivity. Current output measures the weakness; it does not yet prove improvement.
- [2026-06-26] engineering — replaced deprecated `datetime.utcnow()` with timezone-aware UTC.
- [2026-06-26] external-systems — Fund versioned in private GitHub repo; can PR against itself.
