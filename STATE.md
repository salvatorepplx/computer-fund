# Computer Fund — STATE (auto-generated; do not hand-edit)

_Last updated: 2026-06-28T01:01:38.829883+00:00 · HEAD 7830f28_

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
| TICKER:NVDA | 23 (raw 33) | PRELIMINARY_EDGE | 2/0.5078 | circ=False |
| TICKER:RDDT | 17 (raw 27) | PRELIMINARY_EDGE | 2/0.6972 | circ=False |
| TICKER:TSLA | 17 (raw 27) | PRELIMINARY_EDGE | 4/0.4969 | circ=False |
| TICKER:SNDK | 14 (raw 15) | PRELIMINARY_NO_EDGE | 0/0.4367 | circ=False |

## The one honest finding
Seed lead-lag thesis is NOT surviving the permutation null test so far (apparent edges ~ chance).
Pipeline correctly proposes ZERO trades. An honest KILL is a win, not a failure.

## What's blocking the next outcome
No authoritative verdict yet. Deepest: TICKER:NVDA at n_spaced=23 (~1 more time-spaced points to authoritative). Permutation null so far: edges indistinguishable from chance (see lessons.md). Likely KILL+evolve when N hits 24.

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
7830f28 Capture point-in-time external evidence for the 5 research mechanisms (Failure 3)
87a59a6 Capture & commit point-in-time external evidence for the 5 research mechanisms (Failure 3): analyst consensus/PT-revisions + 6q earnings/PEAD for NVDA/RDDT/TSLA/SNDK
6c30d5a web series capture tick (NVDA n_spaced=22, +1 toward N=24 threshold)
1bdb7b6 Structural fix (Failure 2): add pr_queue_drain axis to self_audit; add computer-fund-operating-doctrine skill (Obligations A+B)
b4b0036 Structural fix (Failure 2): operating-doctrine skill + pr_queue self-audit axis
```
