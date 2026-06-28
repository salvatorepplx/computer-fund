# Computer Fund Corpses

Durable log for killed theses, negative diagnostics, and lessons that should feed future
research and simulation seeding. A corpse is valuable because it prevents the Fund from
rediscovering the same bad idea with a new name.

This file is offline/propose-only. It must not touch Robinhood, live market data,
broker/account/order state, ARMED handoffs, sizing, or trading behavior. Do not record
unobserved market outcomes as facts; label deterministic fixtures, simulations, review
notes, and future observed data separately.

## Discipline

When a thesis is killed, add an entry before moving on:

- **Thesis**: the claim that was tested, in one sentence.
- **Status**: `KILLED`, `REJECTED_BEFORE_TEST`, or `SUPERSEDED`.
- **Evidence type**: deterministic fixture, offline simulation diagnostic, code review,
  paper result, or observed historical data. Never blur simulated and observed data.
- **Kill reason**: the falsifier, diagnostic, constraint, or review finding that killed it.
- **Lesson**: the reusable principle to feed back into the seeder.
- **Seeder feedback**: what future research prompts, sim scenarios, or evals should prefer
  or avoid because of this corpse.
- **Reopen criteria**: the exact new evidence required before the thesis can be retried.

## Seeder Feedback Rules

- Prefer theses that explain why a prior corpse failed before proposing a nearby variant.
- Seed sims with corpse cases as adversarial controls, not as success examples.
- Promote falsifiers that killed multiple corpses into `evals/falsification_playbook.md`.
- Treat negative sim-fidelity diagnostics as research constraints until calibrated against
  observed sentiment trajectories.

## Corpses

### 2026-06-26 — Persistent-network / influencer-cascade simulator variants

- **Status**: `KILLED` as improvement candidates for SIM-FIDELITY-1.
- **Evidence type**: offline deterministic sim-fidelity diagnostic plus PR review note;
  this is not an observed market/live trading result.
- **Thesis**: making the sentiment simulator network persistent, or adding an influencer
  cascade multiplier on top of that persistent network, would improve simulator fidelity
  versus the baseline resampled-network fixture.
- **Kill reason**: PR 4 review called out that the persistent-network and
  influencer-cascade variants underperformed the baseline edge in the SIM-FIDELITY
  diagnostics and should be logged as a corpse rather than buried.
- **Lesson**: more realistic-looking diffusion mechanics are not automatically better;
  simulator changes must improve a fidelity metric instead of adding narrative complexity.
- **Seeder feedback**: future simulator-seeding prompts should not re-propose persistent
  network state or influencer cascades as standalone upgrades. They must first identify a
  missing fidelity target, with sentiment lead-lag now the key metric after the placebo
  coverage landed in PR 6 / PR 9.
- **Reopen criteria**: only retry if observed sentiment trajectory data shows a concrete
  lead-lag or calibration failure that the baseline resampled-network simulator cannot
  represent, and the proposed variant pre-registers the eval it should improve.

## Entry Template

Copy this block for each future killed thesis.

```markdown
### YYYY-MM-DD — Short thesis name

- **Status**: `KILLED` / `REJECTED_BEFORE_TEST` / `SUPERSEDED`.
- **Evidence type**: deterministic fixture / offline simulation diagnostic / code review /
  paper result / observed historical data. State whether this is simulated or observed.
- **Thesis**: One sentence claim.
- **Kill reason**: Specific falsifier, diagnostic, constraint, or review finding.
- **Lesson**: Reusable principle.
- **Seeder feedback**: How future research/sim prompts should change.
- **Reopen criteria**: Exact new evidence required before retrying.
```

### 2026-06-27 — Seed thesis: web-sentiment lead-lag predicts NVDA price (FIRST AUTHORITATIVE KILL)

- **Status**: `KILLED`.
- **Thesis**: short-horizon web-search sentiment changes lead NVDA price changes at a positive lag
  (sentiment predates price), generating tradeable alpha — the Fund's seed "predate public sentiment
  on a battle location" hypothesis.
- **Evidence type**: OBSERVED data. 24 time-spaced points (n_spaced=24, de-bursted from 35 raw) of
  Computer-captured web_search_sentiment vs corpus price proxy for TICKER:NVDA, 2026-06-26 → 2026-06-27.
  This is the FIRST verdict to clear the authoritative threshold (n_spaced>=24); all prior verdicts were
  PRELIMINARY and not a basis for capital.
- **Kill reason**: FAILED the permutation null test. `evals/leadlag_real.py` reports verdict=EDGE
  (best_corr=0.5079 at lag 2, non-circular) — but the raw correlation gate is too easy to fool at small N.
  `evals/leadlag_permutation.py` (k=2000 label shuffles, seed=7) gives verdict=EDGE_IS_NOISE,
  p_value=0.2075 (> the 0.10 bar): shuffled-label paths beat the observed correlation ~21% of the time.
  The apparent edge is statistically indistinguishable from chance. The trade gate
  (authoritative EDGE AND non-circular AND permutation p<=0.10) is NOT met. Alpha pipeline correctly
  emits ZERO proposals. No trade placed. This is the system working exactly as designed: an honest KILL.
- **Lesson**: a positive lead-lag correlation that clears a fixed magnitude threshold is NOT evidence of
  alpha at small N — the permutation null is the gate that matters. Earlier preliminary readings (NVDA
  ~0.51–0.64 best_corr) looked encouraging and would have been a trap without the shuffle test. Never let
  the raw-correlation EDGE label authorize anything; the permutation p-value is authoritative.
- **Seeder feedback**: do NOT re-propose "web-search sentiment level/change leads price at a short horizon"
  for the same single-name, single-source setup. Future sentiment theses must either (a) use a different,
  corroborated signal construction (cross-source divergence, mention-velocity acceleration), (b) operate on
  a different horizon/structure, or (c) be tested cross-sectionally (>=30% of a >=30-name universe), not on
  one ticker. Prefer the 5 researched mechanisms now seeded with evidence in
  runs/strategies/research/evidence/ over re-running the seed.
- **Reopen criteria**: a materially different signal (multi-source corroboration or mention-velocity, not
  raw web-sentiment level), tested on a >=30-name universe, that survives the permutation null (p<=0.10)
  AND the circularity guard AND cross-sectional generalization (>=30% of universe) on forward data.

## 2026-06-28 — Permutation gate blocks lead-lag alpha (NVDA authoritative EDGE but p>0.10)

- **Killed thesis**: sentiment lead-lag EDGE implies tradable alpha once n_spaced>=24.
- **Evidence**: latest authoritative series hit n_spaced>=24 for NVDA, but permutation p>0.10 (noise), so no trade is eligible under CHARTER gate.
- **Action**: treat as honest KILL; do not trade; evolve signal model before retrying.

### 2026-06-28 — TSLA raw lead-lag EDGE fails permutation null

- **Status**: `KILLED` as a single-name support case for the seed web-search sentiment lead-lag thesis.
- **Evidence type**: OBSERVED historical data from committed Computer-captured canonical series only;
  offline/propose-only documentation, not live market/account/order state.
- **Thesis**: TICKER:TSLA web-search sentiment changes lead short-horizon price changes strongly enough
  to support tradeable lead-lag alpha after the authoritative n_spaced threshold is met.
- **Kill reason**: `evals/leadlag_real.py` reached the authoritative threshold (`n=24`,
  `n_raw_points=35`, `min_n=24`) and reported raw `verdict=EDGE` (`best_lag=4`,
  `best_corr=0.4605`, `contemp_corr=-0.1965`, `circularity_flag=false`), but the required
  permutation falsifier rejected eligibility: `evals/leadlag_permutation.py` returned
  `verdict=EDGE_IS_NOISE` with `p=0.1575` at `k=2000`, `seed=7`, so
  `significant_at_0.10=false`. The full gate (authoritative EDGE + non-circular + permutation
  p<=0.10) is not met.
- **Lesson**: TSLA independently confirms the NVDA failure mode: a clean-looking, non-circular raw
  lead-lag EDGE at n_spaced>=24 is still not capital-eligible when shuffled-label paths can plausibly
  match or beat it. Raw correlation is a diagnostic, not a trade signal.
- **Seeder feedback**: do not seed nearby single-ticker web-search sentiment lead-lag variants that
  optimize lag/correlation alone. Future variants must explain how they improve permutation
  significance, add cross-sectional support, or change the signal family/null test before any
  PROPOSED artifact is considered.
- **Reopen criteria**: retry only if TSLA or a broader cross-sectional basket clears the complete gate
  (authoritative n_spaced>=24, `circularity_flag=false`, and permutation `p<=0.10`) on committed
  observed data, or if a pre-registered replacement null test supersedes the current permutation gate.

### 2026-06-28 — RDDT lead-lag EDGE survives the permutation null but rides a DEGENERATE price proxy

- **Status**: `KILLED` (proposal withdrawn to `runs/KILLED/battle-RDDT-leadlag-2026-06-28.json` before ARM). Not traded.
- **Evidence type**: OBSERVED committed canonical series only (`runs/sentiment/series/TICKER_RDDT.jsonl`); offline diagnostic, no live broker/account/order touch.
- **Thesis**: TICKER:RDDT web-search sentiment changes lead short-horizon price changes (raw `verdict=EDGE`, `best_lag=2`, `best_corr=0.6522`, `circularity_flag=false`, n_spaced=24) strongly enough to trade after the full gate is met.
- **What I checked (chip-on-shoulder, per V2 handoff)**: the handoff flagged this EDGE as a bug suspect because it appeared right after the #46/#47 scorer-bias fixes. Two findings:
  1. **The scorer-change suspicion is CLEARED**: 32 of 35 raw points predate the scorer change (#46 03:05Z / #47 03:24Z); on RDDT the `score` vs `score_raw` divergence is negligible (mean +0.0014, max ±0.07). The edge is not manufactured by the mid-thesis signal change.
  2. **The permutation null is ROBUST**: p = 0.0345 / 0.0465 / 0.0435 / 0.038 / 0.036 across seeds 7/1/42/123/2024 — all `significant_at_0.10=True`. Not a single-seed fluke.
- **Kill reason (the defect the permutation test cannot see)**: the `price_proxy` series the lead-lag correlates against is **degenerate**. Across the 24 de-bursted points there are only **9 distinct price values** (167.0×7, 166.71×5, 162.37×5, …), **8 of 23 consecutive price-changes are exactly ZERO**, and there is a **24.1h capture gap** mid-series (the overnight hard-coded-path stall). The corpus price extractor is returning repeated/stuck boilerplate quotes, so the lead-lag is correlating real sentiment drift against a **step-function price artifact**, not real price discovery. A permutation test that shuffles *sentiment* labels against a corrupted *price* axis cannot detect the corruption — so a low p does NOT certify a tradeable edge. CHARTER: data quality is upstream of every verdict; no look-ahead, no fabrication.
- **Lesson**: a robust permutation p is necessary but NOT sufficient. The null model only stress-tests the label axis; it assumes the OTHER axis (price) is trustworthy. Before trusting any lead-lag p-value, audit the price series for degeneracy (distinct-value count, zero-return fraction, capture gaps). See `corpus/lessons.md` 2026-06-28 entry.
- **Diagnostic**: `scripts/diag_rddt_scorer_boundary.py`.
- **Reopen criteria**: RDDT (or a cross-sectional basket) clears the full gate on a NON-degenerate price series — a real per-capture quote (live Robinhood/finance quote, not corpus-extracted), >=15 distinct price values with <20% zero-return fraction over n_spaced>=24, no multi-hour capture gaps, AND permutation p<=0.10.

### 2026-06-28 — RDDT lead-lag "EDGE" killed: permutation can't see a degenerate price axis

- **Status**: `KILLED`. The PROPOSED artifact (battle-RDDT-leadlag-2026-06-28) was withdrawn to
  `runs/KILLED/`. NOT ARMED. No order placed.
- **Evidence type**: OBSERVED committed canonical series only; offline/propose-only.
- **Thesis**: RDDT web-search sentiment changes lead short-horizon price changes (best_lag=2,
  best_corr=0.6522), authoritative n_spaced=24, non-circular, permutation p=0.0345
  (EDGE_SURVIVES_NULL, seed-robust p in [0.032,0.0465] across 8 seeds).
- **Why killed despite passing the literal gate**: the `price_proxy` axis the lead-lag correlates
  against is DEGENERATE. Across the 24 de-bursted points there are only ~9 distinct price values
  (167.0 x7, 166.71 x5, 162.37 x5), 8 of 23 consecutive price-changes are exactly ZERO, plus a
  24.1h capture gap mid-series and a lone corpus-extraction spike (192.72 vs ~167 neighbors). The
  corpus price extractor is returning stuck/repeated boilerplate quotes, so the "edge" is real
  sentiment drift correlated against a step-function price artifact, not real price discovery.
- **The key lesson**: a permutation test that shuffles SENTIMENT labels cannot detect a corrupted
  PRICE axis. p=0.0345 certifies "this sentiment ordering is unusual vs shuffles" — it says nothing
  about whether the price series is valid. Robustness probes (drop-worst-point, winsorize, reseed,
  drop-tail) ALSO ran on the same degenerate prices and so falsely "confirmed" the edge. Data
  quality is upstream of every verdict and upstream of every null test.
- **NOT a #46/#47 scorer artifact**: 32/35 points predate the scorer change; score vs score_raw
  divergence on RDDT is negligible (mean +0.0014). The original suspicion (scorer non-stationarity)
  was the wrong bug; the real bug was the price axis. (Two suspicions, the deeper one won.)
- **Diagnostics**: `scripts/diag_rddt_scorer_boundary.py` (price-axis degeneracy + scorer boundary),
  `scripts/spike_rddt_robustness.py` (perturbation probes — useful but blind to the price-axis flaw).
- **Reopen criteria**: RDDT (or a cross-sectional basket) clears the full gate on a NON-degenerate
  price series: a real per-capture live quote (Robinhood/finance, not corpus-extracted), >=15
  distinct price values with <20% zero-return fraction over n_spaced>=24, no multi-hour capture
  gaps, AND permutation p<=0.10.
