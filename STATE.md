# Computer Fund — STATE (auto-generated; do not hand-edit)

_Last updated: 2026-06-28T01:15:11.088450+00:00 · HEAD 2f335e6_

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
| TICKER:NVDA | 24 (raw 34) | EDGE | 2/0.5079 | circ=False |
| TICKER:RDDT | 17 (raw 27) | PRELIMINARY_EDGE | 2/0.6972 | circ=False |
| TICKER:TSLA | 17 (raw 27) | PRELIMINARY_EDGE | 4/0.4969 | circ=False |
| TICKER:SNDK | 14 (raw 15) | PRELIMINARY_NO_EDGE | 0/0.4367 | circ=False |

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
2f335e6 Restore heartbeat: recreate 3 crons (capture 80400d62 / watch 2dff0abe / self-audit 98c3d3f3) lost with source sandbox; commit trigger scripts + runs/CRONS.md
6d27e68 web series capture tick (NVDA n_spaced=23, 1 from authoritative)
7830f28 Capture point-in-time external evidence for the 5 research mechanisms (Failure 3)
87a59a6 Capture & commit point-in-time external evidence for the 5 research mechanisms (Failure 3): analyst consensus/PT-revisions + 6q earnings/PEAD for NVDA/RDDT/TSLA/SNDK
6c30d5a web series capture tick (NVDA n_spaced=22, +1 toward N=24 threshold)
```
