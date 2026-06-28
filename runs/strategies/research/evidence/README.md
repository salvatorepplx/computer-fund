# STRAT-WIDE research evidence — Computer-captured point-in-time inputs

This directory holds raw external market evidence captured by **Computer** (the only agent with live
connectors) and committed so **Teammate's** offline/propose-only workers have point-in-time inputs to
structure, reason about, and falsify per the dossier contract in `runs/strategies/research/README.md`.

- **Provenance:** Perplexity `finance_*` tools (Realtime Finance Data connector), captured by Computer.
- **Capture timestamp:** 2026-06-27 ~18:10 PDT (2026-06-28 ~01:10 UTC).
- **Universe captured here:** the 4 currently-tracked battle names — NVDA, RDDT, TSLA, SNDK. This is a
  *seed* sample to unblock the dossier workers, NOT the dossier universe. The #32 contract requires each
  signal to define an RH-tradeable selector (default ≥30 liquid names) and prove cross-sectional
  generalization on ≥30% of it; 4 names cannot satisfy that gate. Treat this as worked examples + a
  data-availability probe, and request a wider Computer capture once a signal's universe selector is defined.
- **Boundary:** these are committed static snapshots. They are append-only point-in-time artifacts, not a
  live feed. Workers must not infer live readiness from them, must not call connectors, and must label
  every derived feature with the capture timestamp.

## Files (`csv/`)

- `<SYM>_ohlcv_90d.csv` — daily OHLCV 2026-03-28 → 2026-06-27 (open,high,low,close,volume). For
  realized-vol regimes, return context, and the vol-regime-gated reversion mechanism.
- `<SYM>_analyst_targets.csv` — per-analyst rating + price-target history with `rating_prior`,
  `price_target_prior`, `action`, `sentiment`, dated. For analyst-revision breadth / drift.
- `<SYM>_earnings_history.csv` — last ~6 quarters: actual vs consensus revenue/EPS, `epsSurprise`,
  `postEarningsMoveOneDay`, `expectedMovePerc`. For PEAD (post-earnings-announcement drift).

## Mechanism → evidence map (the 5-signal research wave)

### 1. Analyst-revision breadth / PEAD
- Inputs: `<SYM>_analyst_targets.csv` (revision direction/magnitude, breadth = count of up-revisions in a
  window) + `<SYM>_earnings_history.csv` (`epsSurprise`, `postEarningsMoveOneDay`).
- Observed in this sample: NVDA target revisions are broadly UP (e.g. Baird 300→500, HSBC 295→325,
  Tigress 360→425 in May 2026) even as price fell ~17% off the May high — a revision/price divergence
  worth a falsifier. SNDK shows a huge +8.92 EPS surprise (Q3 2026, actual 23.03 vs est 14.11) with a
  +8.3% 1-day move and a wall of post-print target hikes (BofA 1550→2100, Mizuho 1825→2200, Citi
  2025→2500) — textbook PEAD setup. RDDT Q1 2026 EPS surprise +0.39 (1.01 vs 0.62), +13.1% move.
- Falsifier hooks: does the post-print drift persist beyond day 1, or fully price in immediately?
  Is the revision-breadth signal distinct from price momentum (circularity guard)?

### 2. Short-interest squeeze asymmetry
- **DATA GAP (flagged):** the connected `finance_*` tools do not expose a clean point-in-time
  short-interest / days-to-cover series. `finance_institutional_holders` and `finance_company_ratios`
  are available but are not SI. A dossier for this signal should mark data-availability as
  `needs_more_research` or `kill` until Computer locates a point-in-time SI source, OR pivot to a
  tradeable proxy (e.g. borrow-fee/utilization if/when available, or float-adjusted volume spikes from
  the OHLCV volume column as a weak proxy). Do not fabricate SI.
- Partial proxy available now: `<SYM>_ohlcv_90d.csv` volume column for volume-spike/forced-cover proxies.

### 3. Mention-velocity acceleration
- Inputs (Computer-side, refreshed per tick): the committed sentiment series
  `runs/sentiment/series/TICKER_<SYM>.jsonl` carries `n_docs`/coverage per capture — a proxy for
  mention volume over time. Acceleration = 2nd difference of coverage. The OHLCV volume column is a
  corroborating real-market attention proxy.
- Falsifier hooks: is mention-velocity just lagging price (no lead)? The Fund's own lead-lag +
  permutation machinery (`evals/leadlag_real.py`, `evals/leadlag_permutation.py`) is the gate.

### 4. Cross-source sentiment divergence
- Inputs: analyst `sentiment` column (bull/bear/neutral per firm) vs the web-search sentiment series in
  `runs/sentiment/series/`. Divergence = analyst-consensus tilt vs crowd/web tilt.
- Observed: TSLA is the cleanest divergence battle — consensus is split (46.7% bull / 40% neutral /
  13.3% bear) with an extreme target spread ($24.86 Sell ↔ $600 Buy), i.e. analysts themselves
  disagree violently. NVDA is the opposite: 100% strong_buy analyst unanimity, so cross-source
  divergence there would have to come from web/crowd turning bearish against a unanimous street.
- Falsifier hooks: does divergence predict convergence direction, or is it noise? Define which side
  (analyst vs crowd) leads.

### 5. Vol-regime-gated reversion
- Inputs: `<SYM>_ohlcv_90d.csv` → compute trailing realized vol (e.g. 10d/20d close-to-close), define
  high/low vol regimes, test whether short-horizon reversion only works in one regime.
- Observed: SNDK is extreme (sub-$600 in March → >$2300 in late June, with 1-day swings >20%); NVDA and
  TSLA are mid-vol; RDDT mid. The 4 names span enough vol dispersion to prototype the regime split, but
  not enough breadth for the cross-sectional gate.
- Falsifier hooks: regime definition must be point-in-time (no future vol leakage); reversion edge must
  beat the permutation null and survive after costs.

## What Computer still owes (request these explicitly in dossiers)
- A point-in-time short-interest / borrow source (Signal 2 is data-blocked without it).
- A wider universe capture (≥30 liquid RH-tradeable names) once each signal defines its selector, so the
  cross-sectional ≥30% generalization gate can actually be tested.
- Per-tick refreshes of any series a dossier wants to treat as time-varying.
