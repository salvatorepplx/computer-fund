# Computer Fund Lessons

Durable lessons distilled from killed theses, negative diagnostics, and review findings.
This is the seeder-facing companion to `runs/CORPSES.md`: CORPSES records what died;
this file records what future research should remember before proposing nearby variants.

This file is offline/propose-only. It must not touch Robinhood, live market data,
broker/account/order state, ARMED handoffs, sizing, or trading behavior. Lessons may
reference observed historical data only when provenance is explicit; deterministic
fixtures, simulations, and review notes must stay labeled as such.

## Discipline

When a corpse produces a reusable rule, add a lesson with these required fields:

- **Source corpse**: the `runs/CORPSES.md` entry or other offline artifact that produced the lesson.
- **Reusable lesson**: the general principle, not just a restatement of one failed thesis.
- **Seeder rule**: what future thesis-seeding prompts should prefer, avoid, or require.
- **Meta/eval linkage**: how the lesson should appear in offline review, especially the
  `memory_lessons` axis in `evals/meta_orchestrator.md` or a named deterministic eval.
- **Revisit trigger**: the exact new evidence that should cause the Fund to reconsider the lesson.

## Lessons

### 2026-06-26 — Narrative complexity must earn fidelity

- **Source corpse**: `runs/CORPSES.md` entry "Persistent-network / influencer-cascade simulator variants".
- **Reusable lesson**: realistic-looking sentiment diffusion mechanics are not automatically better;
  simulator changes must improve a named fidelity, lead-lag, or calibration metric.
- **Seeder rule**: future simulator seeds should not propose persistent network state or influencer
  cascades as standalone upgrades. They must name the missing fidelity target and the offline eval
  expected to improve before implementation.
- **Meta/eval linkage**: weekly meta passes should score repeated attempts to reintroduce these variants
  without new evidence as a `memory_lessons` regression; relevant evidence is this file plus
  `runs/CORPSES.md`.
- **Revisit trigger**: observed sentiment trajectory fixtures show a concrete lead-lag or calibration
  failure that the baseline resampled-network simulator cannot represent.

## Entry Template

Copy this block for each future distilled lesson.

```markdown
### YYYY-MM-DD — Short lesson name

- **Source corpse**: Link to `runs/CORPSES.md` entry or other offline artifact.
- **Reusable lesson**: General principle.
- **Seeder rule**: How future thesis prompts should change.
- **Meta/eval linkage**: `memory_lessons` evidence and/or named deterministic eval.
- **Revisit trigger**: Exact new evidence required before changing the lesson.
```

## 2026-06-26 — Substrate swap + burst-vs-time lesson (web_search > finance connector)
- KILLED reliance on finance_ticker_sentiment: 401 UNAUTHORIZED under any load; it is a
  static summarizer, not a moving signal. robinhood get_equity_quotes also 401ing (env-wide
  connector auth blip, not our code). Building lead-lag alpha on those = building on sand.
- NEW substrate: pplx_sdk.search.web (execution/web_sentiment.py). Reliable, no-auth,
  timestamped, MOVES as news moves, and carries explicit parseable readings (Adanos
  "% bullish across N sources", Stocktwits "extremely bearish", Perplexity Finance
  bull/bear split + analyst consensus, "Strong Buy/Sell"). Scorer blends explicit
  readings (high weight) + lexical bull/bear balance + EWMA. Self-tests discriminate
  bull(+0.67)/bear(-0.91)/mixed correctly. Confidence 0.95 on 16-doc corpus vs 0.2-0.65
  single noisy finance fetch. Price proxy now extracted from corpus (median of dense band)
  — reliable, with robinhood as fallback only.
- LESSON (burst vs time): bursting captures builds N fast but NOT real time-variation —
  intraday news corpus is slow-moving, so EWMA converges to a fixed point within a burst.
  Lead-lag on burst data = convergence artifacts (labeled PRELIMINARY, not capital-grade).
  A trustworthy verdict needs TIME-SPACED points (the */30 cron), where news actually
  changes between captures. Burst proved the pipeline end-to-end; cron produces the verdict.
- Equilibria from burst (calibration sanity, matches real narratives): NVDA ~+0.26 (Strong
  Buy but technically weak), RDDT ~+0.40 (Moderate/Strong Buy), TSLA ~+0.07 (range-bound/mixed).

## 2026-06-26 — Split-series bug (caught via cron-result cross-check)
- BUG: capture cron invoked capture_web_tick.py with lowercase bare symbols (nvda/rddt/tsla),
  which wrote to nvda.jsonl etc. — a PARALLEL series from the canonical TICKER_NVDA.jsonl that
  my burst captures used. Two fragmented series, neither feeding the other => silently ~2x'd
  time-to-verdict and corrupted the lead-lag input. Spotted because the cron result reported
  "series now 2 points" while local canonical files had 15 — the discrepancy was the tell.
- FIX: canonical_entity() in capture_web_tick.py normalizes ANY invocation
  (nvda / NVDA / TICKER:NVDA) -> TICKER:NVDA, so the series file is stable regardless of caller.
  Merged orphan points back in (no data lost): NVDA 17, RDDT/TSLA 13. Removed orphan files.
- LESSON: cross-check cron-reported state against ground-truth files every time. A subagent
  cron can invoke a script differently than intended; idempotency must live IN the script, not
  in the caller's discipline. State belongs in canonical files, normalized at the boundary.

## 2026-06-26 — Time-spacing the lead-lag (de-bursting) + small-N honesty
- Added time-spacing to leadlag_real.py: collapse captures <180s apart to the last in
  the cluster, so each retained point is genuine new info. NVDA 17 raw -> 8 time-spaced.
  Drops null-price rows too. Reports both n (spaced) and n_raw_points.
- HONESTY: with n_spaced=4-8 and small lag windows, best_corr trivially saturates to +/-1.0.
  That is small-N artifact, NOT edge. Probe correctly keeps verdict PRELIMINARY (non-authoritative
  until n>=24). Bursting cannot fix this — only TIME (the */30 cron) adds real spaced points.
- IMPLICATION: stop bursting for "depth"; it inflates n_raw but not n_spaced. The verdict is
  gated on wall-clock accumulation. Patience is the correct move now, not more captures.

## 2026-06-26 — Circularity / lookahead guard (chip-on-shoulder self-audit)
- Self-audited: is the sentiment score circular with price (reading price action back as
  "sentiment")? Contemporaneous corr(sentiment_level, price_level): RDDT +0.007, TSLA +0.034
  (clean, distinct signal) but NVDA +0.62 (yellow flag — possible mild circularity, inflated
  by early burst points spanning a wide price range).
- ADDED circularity guard to leadlag_real.py: compute contemp_corr; if |corr|>=0.6 set
  circularity_flag and BLOCK an EDGE verdict regardless of lead-lag. A possibly-circular
  signal must not masquerade as alpha. NVDA now flagged; RDDT/TSLA clean.
- Conservative by design: better to under-claim edge than trade on lookahead. Expect NVDA's
  contemp_corr to settle as genuinely time-spaced points replace burst inflation.

## 2026-06-26 — Price extraction hardening (SNDK exposed it)
- BUG: corpus price extractor (blind median of $-figures) failed badly on SNDK:
  bimodal corpus (small EPS/%/target figures + real ~$2316 quote) -> median landed at $112,
  then $21. Also: SNDK trades ~$2316, ABOVE the old $2000 sane-band cap -> real price excluded.
- FIXES (all generic, not SNDK-specific):
  1. Context-aware scoring: prefer $-figures with cents + near price-cue words ("closed at",
     "trading at", "shares", "current") + near the ticker. NVDA/TSLA/RDDT now spot-on.
  2. Raised band cap 2000 -> 5000; added a dedicated "stock price quote today closed at" query
     so every name gets a clean live-quote doc in its corpus.
  3. Series-consistency gate: reject a corpus price >35% off the last good price for that name
     (real intraday moves between captures rarely exceed that) -> fall back to broker, else hold
     last. SNDK's noisy price correctly REJECTED (held_last) instead of corrupting the series.
- LESSON: financial text is full of non-price $-figures; never trust a blind aggregate. Gate
  new data against history. A bad price proxy silently corrupts the lead-lag — data quality is
  upstream of every verdict.

## 2026-06-26 — Accelerate the verdict honestly (cadence, not bursting)
- Confronted the real bottleneck: authoritative lead-lag needs ~24 time-spaced pts; at */30
  that's ~8h. The goal is the FIRST TRADE, not endless hardening. Need a faster HONEST path.
- LEVER: tightened capture cron */30 -> */10. Every 10-min point is still >3min apart (de-burst
  threshold) = genuine new info, NOT bursting. Time-to-verdict ~8h -> ~2.5h. Legitimate accel.
- Rejected the dishonest shortcut (lowering N without a significance test). N stays 24 OR a
  proper p-value gate later; never fake the verdict.
- ACCOUNTABILITY: by ~16:00 PDT today, NVDA (the deepest series) should approach n_spaced~24 ->
  first AUTHORITATIVE verdict (EDGE or KILL). If EDGE & not circular -> alpha pipeline -> first
  tiny trade. If KILL -> seed strategy falsified, evolve/replace per constitution. Either is a win.
