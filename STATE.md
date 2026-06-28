# Computer Fund — STATE (auto-generated; do not hand-edit)

_Last updated: 2026-06-28T01:22:31.011928+00:00 · HEAD 10f6a45_

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
| TICKER:NVDA | 25 (raw 35) | EDGE | 2/0.5078 | circ=False |
| TICKER:RDDT | 18 (raw 28) | PRELIMINARY_EDGE | 2/0.6922 | circ=False |
| TICKER:TSLA | 18 (raw 28) | PRELIMINARY_EDGE | 4/0.4931 | circ=False |
| TICKER:SNDK | 15 (raw 16) | PRELIMINARY_NO_EDGE | 0/0.4229 | circ=False |

## The one honest finding
Seed lead-lag thesis is NOT surviving the permutation null test so far (apparent edges ~ chance).
Pipeline correctly proposes ZERO trades. An honest KILL is a win, not a failure.

## What's blocking the next outcome
An authoritative EDGE exists: TICKER:NVDA -> run alpha_pipeline, review, place.

## Single next action
Promote the authoritative EDGE via alpha_pipeline -> PROPOSED -> safety review -> trade.

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
10f6a45 Add vol regime reversion dossier (#39)
4b36118 Add short-interest squeeze dossier (#38)
18ededd Add cross-source sentiment divergence dossier (#37)
dd0e006 Add mention velocity acceleration dossier (#36)
ad6a957 Add analyst revision breadth dossier (#35)
```
