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
