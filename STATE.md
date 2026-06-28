# Computer Fund — STATE (auto-generated; do not hand-edit)

_Last updated: 2026-06-28T03:07:43.546155+00:00 · HEAD cd292e8_

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
| TICKER:NVDA | 30 (raw 40) | EDGE | 2/0.5039 | circ=False; perm=EDGE_IS_NOISE p=0.1505 sig=False |
| TICKER:RDDT | 23 (raw 33) | PRELIMINARY_EDGE | 2/0.6575 | circ=False; perm=PRELIMINARY_SIGNIFICANT p=0.041 sig=True |
| TICKER:TSLA | 23 (raw 33) | PRELIMINARY_EDGE | 4/0.4645 | circ=False; perm=PRELIMINARY_NULL p=0.1745 sig=False |
| TICKER:SNDK | 20 (raw 21) | PRELIMINARY_NO_EDGE | 0/0.384 | circ=False; perm=PRELIMINARY_NULL p=0.1965 sig=False |
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
cd292e8 state: advance last seen after PR46 merge
916da95 Guard web sentiment against quote boilerplate bias (#46)
cfdb9d5 state: advance slack last_seen_ts
8e3e2b2 [sal-bot Teammate] Skip parked axes for self-audit queue (#45)
c6a2877 web series capture tick
```
