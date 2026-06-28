# Computer Fund — STATE (auto-generated; do not hand-edit)

_Last updated: 2026-06-28T03:25:22.213918+00:00 · HEAD b558e89_

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
| TICKER:NVDA | 31 (raw 42) | EDGE | 2/0.5039 | circ=False; perm=EDGE_IS_NOISE p=0.132 sig=False |
| TICKER:RDDT | 24 (raw 35) | EDGE | 2/0.6522 | circ=False; perm=EDGE_SURVIVES_NULL p=0.0345 sig=True |
| TICKER:TSLA | 24 (raw 35) | EDGE | 4/0.4605 | circ=False; perm=EDGE_IS_NOISE p=0.1575 sig=False |
| TICKER:SNDK | 21 (raw 23) | PRELIMINARY_NO_EDGE | 0/0.3638 | circ=False; perm=PRELIMINARY_NULL p=0.2165 sig=False |
| TICKER:CRM | 0 (raw 0) | INSUFFICIENT | None/None | circ=None; perm=INSUFFICIENT p=None sig=None |
| TICKER:PATH | 0 (raw 0) | INSUFFICIENT | None/None | circ=None; perm=INSUFFICIENT p=None sig=None |

## The one honest finding
At least one lead-lag thesis survives the authoritative raw EDGE, circularity, and permutation gates. Pipeline may emit PROPOSED artifacts, not orders.

## What's blocking the next outcome
Trade-eligible EDGE exists after permutation gate: TICKER:RDDT -> run alpha_pipeline for PROPOSED review handoff.

## Single next action
Run alpha_pipeline; only PROPOSED artifacts that survive safety review may advance.

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
b558e89 Remove strong lexical bullish bias (#47)
374f47b web series capture tick
cd292e8 state: advance last seen after PR46 merge
916da95 Guard web sentiment against quote boilerplate bias (#46)
cfdb9d5 state: advance slack last_seen_ts
```
