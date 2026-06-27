# Computer Fund — STATE (auto-generated; do not hand-edit)

_Last updated: 2026-06-27T00:50:03.780209+00:00 · HEAD dcced73_

THE FRONT DOOR. Any agent waking cold (Computer, background cron, Teammate) reads this FIRST.
Regenerated every capture tick by scripts/state_snapshot.py from ground truth — never stale.

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
| TICKER:NVDA | 21 (raw 31) | PRELIMINARY_EDGE | 2/0.5104 | circ=False |
| TICKER:RDDT | 15 (raw 25) | PRELIMINARY_EDGE | 2/0.7245 | circ=False |
| TICKER:TSLA | 15 (raw 25) | PRELIMINARY_EDGE | 4/0.7686 | circ=False |
| TICKER:SNDK | 12 (raw 13) | PRELIMINARY_NO_EDGE | 0/0.4597 | circ=False |

## The one honest finding
Seed lead-lag thesis is NOT surviving the permutation null test so far (apparent edges ~ chance).
Pipeline correctly proposes ZERO trades. An honest KILL is a win, not a failure.

## What's blocking the next outcome
No authoritative verdict yet. Deepest: TICKER:NVDA at n_spaced=21 (~3 more time-spaced points to authoritative). Permutation null so far: edges indistinguishable from chance (see lessons.md). Likely KILL+evolve when N hits 24.

## Single next action
Keep capturing (cron */10). When deepest name hits n_spaced>=24, the verdict is authoritative: if it survives permutation (p<=0.10) -> trade; else KILL seed thesis, evolve.

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
dcced73 web series capture tick
22e2fcd web series capture tick
2af7050 Correct the breadth mistake: generation != theses. Demote 12 auto-tuples; add evidence ladder
1b37208 Go WIDE: strategy portfolio over a 4800-tuple OPEN hypothesis space (was 1 thesis)
20fb681 Fix transient INSUFFICIENT verdict bug: defensive series read (skip torn lines)
```
