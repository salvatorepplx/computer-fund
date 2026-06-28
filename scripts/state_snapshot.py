"""
Generate STATE.md — the canonical wake-state doc every agent (Computer, a cold
background cron, Teammate) reads FIRST. Auto-derived from repo-local ground
truth at snapshot time, but it can lag later commits because the capture wrapper
refreshes STATE.md before committing the tick. Cold agents should compare the
STATE header HEAD with current git HEAD/origin and inspect intervening commits
when they differ. Run during every capture tick.

Sections: identity/mission pointer, hard rails, current series depth, live
verdicts, the one honest finding, what's blocking the next outcome, and the
single next action. No prose that isn't derived from files.
"""
from __future__ import annotations
import sys, json, subprocess, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from evals.leadlag_real import probe
from execution.ingest_runner import load_series

NAMES = ["TICKER:NVDA", "TICKER:RDDT", "TICKER:TSLA", "TICKER:SNDK"]


def _git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


def build() -> str:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    phase = json.loads((ROOT / "state" / "risk_phase.json").read_text())
    head = _git("rev-parse", "--short", "HEAD")
    recent = _git("log", "--oneline", "-5")

    rows = []
    authoritative_edge = []
    for e in NAMES:
        try:
            v = probe(e)
        except Exception as ex:
            rows.append(f"| {e} | ERR | — | — | {str(ex)[:30]} |")
            continue
        n = v.get("n"); verdict = v.get("verdict"); circ = v.get("circularity_flag")
        nraw = v.get("n_raw_points")
        rows.append(f"| {e} | {n} (raw {nraw}) | {verdict} | {v.get('best_lag')}/{v.get('best_corr')} | circ={circ} |")
        if v.get("authoritative") and verdict == "EDGE" and not circ:
            authoritative_edge.append(e)

    # find the deepest series + how far from authoritative (n_spaced>=24)
    depths = {e: probe(e).get("n", 0) for e in NAMES}
    deepest = max(depths, key=depths.get)
    gap = max(0, 24 - depths[deepest])

    blocking = ("An authoritative EDGE exists: " + ", ".join(authoritative_edge) +
                " -> run alpha_pipeline, review, place." ) if authoritative_edge else (
        f"No authoritative verdict yet. Deepest: {deepest} at n_spaced={depths[deepest]} "
        f"(~{gap} more time-spaced points to authoritative). Permutation null so far: edges "
        f"indistinguishable from chance (see lessons.md). Likely KILL+evolve when N hits 24.")

    next_action = ("Promote the authoritative EDGE via alpha_pipeline -> PROPOSED -> safety review -> trade."
                   if authoritative_edge else
                   "Keep capturing (cron */10). When deepest name hits n_spaced>=24, the verdict is "
                   "authoritative: if it survives permutation (p<=0.10) -> trade; else KILL seed thesis, evolve.")

    return f"""# Computer Fund — STATE (auto-generated; do not hand-edit)

_Last updated: {now} · HEAD {head}_

THE FRONT DOOR. Any agent waking cold (Computer, background cron, Teammate) reads this FIRST.
Regenerated during each capture tick by scripts/state_snapshot.py from repo-local ground truth.
It can lag commits created after the refresh: compare this header HEAD to current git HEAD/origin,
and inspect intervening commits when they differ.

## Mission
Recursively self-improving sentiment-alpha trading system. Generate alpha by predating public
sentiment on contested "battle locations". Real money via Robinhood. Soul = CONSTITUTION.md.

## Hard rails (LAW — never self-improved away; full detail in CHARTER.md)
- Trade ONLY Agentic account 696264779. Roth IRA / margin HARD-EXCLUDED.
- Risk phase: {phase.get('phase_name')} (phase {phase.get('phase')}). Caps: {phase.get('caps')}.
- No per-trade human confirm (Sal granted autonomy within % caps). Kill-switch per CHARTER.
- A trade requires: authoritative EDGE (n_spaced>=24) AND non-circular AND permutation p<=0.10.

## Current series + verdicts
| entity | n_spaced | verdict | best_lag/corr | flags |
|---|---|---|---|---|
{chr(10).join(rows)}

## The one honest finding
Seed lead-lag thesis is NOT surviving the permutation null test so far (apparent edges ~ chance).
Pipeline correctly proposes ZERO trades. An honest KILL is a win, not a failure.

## What's blocking the next outcome
{blocking}

## Single next action
{next_action}

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
{recent}
```
"""


if __name__ == "__main__":
    out = build()
    (ROOT / "STATE.md").write_text(out)
    print("wrote STATE.md")
