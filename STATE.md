# Computer Fund — STATE (auto-generated; do not hand-edit)

_Last updated: 2026-06-28T01:54:01.809610+00:00 · HEAD 2d64216_

THE FRONT DOOR. Any agent waking cold (Computer, background cron, Teammate) reads this FIRST.
Regenerated during each capture tick by scripts/state_snapshot.py from repo-local ground truth.
It can lag commits created after the refresh: compare this header HEAD to current git HEAD/origin,
and inspect intervening commits when they differ.

## Mission
Recursively self-improving sentiment-alpha trading system. Generate alpha by predating public
sentiment on contested "battle locations". Real money via Robinhood. Soul = CONSTITUTION.md.

## Hard rails (LAW — never self-improved away; full detail in CHARTER.md)
- Trade ONLY Agentic account 696264779. Roth IRA / margin HARD-EXCLUDED.
- Risk phase: Unproven (phase 0). Caps: {'single_pos_frac': 0.2, 'option_premium_frac': 0.15, 'cash_floor_frac': 0.25}.
- No per-trade human confirm (Sal granted autonomy within % caps). Kill-switch per CHARTER.
- A trade requires: authoritative EDGE (n_spaced>=24) AND non-circular AND permutation p<=0.10.

## Current series + verdicts
| entity | n_spaced | verdict | best_lag/corr | flags |
|---|---|---|---|---|
| TICKER:NVDA | 27 (raw 37) | EDGE | 2/0.5078 | circ=False; perm=EDGE_IS_NOISE p=0.1635 sig=False |
| TICKER:RDDT | 20 (raw 30) | PRELIMINARY_EDGE | 2/0.6758 | circ=False; perm=PRELIMINARY_SIGNIFICANT p=0.0435 sig=True |
| TICKER:TSLA | 20 (raw 30) | PRELIMINARY_EDGE | 4/0.4683 | circ=False; perm=PRELIMINARY_NULL p=0.2225 sig=False |
| TICKER:SNDK | 17 (raw 18) | PRELIMINARY_NO_EDGE | 0/0.4006 | circ=False; perm=PRELIMINARY_NULL p=0.2555 sig=False |
| TICKER:CRM | 0 (raw 0) | INSUFFICIENT | None/None | circ=None; perm=INSUFFICIENT p=None sig=None |
| TICKER:PATH | 0 (raw 0) | INSUFFICIENT | None/None | circ=None; perm=INSUFFICIENT p=None sig=None |

## The one honest finding
Seed lead-lag thesis is NOT surviving the permutation null test so far (apparent edges ~ chance). Pipeline correctly proposes ZERO trades. An honest KILL is a win, not a failure.

## What's blocking the next outcome
Raw authoritative EDGE failed the permutation trade gate: TICKER:NVDA. Alpha pipeline should have no eligible proposal; KILL+evolve the thesis.

## Single next action
Respect alpha_pipeline zero-eligible outcome; record the KILL/corpse and evolve the thesis.

## Where things live
- Soul/law: CONSTITUTION.md, CHARTER.md, HANDOFF.md
- Signal: execution/web_sentiment.py, scripts/capture_web_tick.py (canonicalizes entity at boundary)
- Capture tick (cron 8cdef537, */10): scripts/capture_and_commit.sh (ONE hardened wrapper)
- Watch tick (cron 63e8ce5f, */5): reads #sal-teammate for @computer / ARMED handoffs
- Verdict: evals/leadlag_real.py + evals/leadlag_permutation.py
- Pipeline: execution/alpha_pipeline.py -> runs/PROPOSED/ (propose-only) ; safety: execution/safety.py
- Lessons (READ THIS): corpus/lessons.md · backlog: runs/QUEUE.json · improvement: corpus/improvement_log.md

## Recent commits
```
2d64216 [sal-bot Teammate] Add min_n to insufficient leadlag telemetry (#42)
f102803 Clarify Teammate proposal flow in handoff (#41)
a38de17 Record corpse: permutation gate blocks alpha; add lesson
64b8405 web series capture tick
97f393a Expand tracked universe (add CRM, PATH) + self-audit
```
