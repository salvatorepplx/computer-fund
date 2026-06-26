"""GEPA-style reflective self-improvement engine.

Reads the latest eval scores, finds the worst-performing eval with an actionable
reference-file handle, drafts a proposed diff against that reference, and writes a
Harness PR for user approval.

NOT auto-applied — every change is gated by user confirm_action.

Usage:
    python self_improve.py                # propose next Harness PR
    python self_improve.py --dry-run      # show what it would propose
"""
from __future__ import annotations
import argparse, json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
SCORES = EVALS / "scores"
HARNESS = ROOT / "references" / "HARNESS-PRS"
HARNESS.mkdir(parents=True, exist_ok=True)

# Maps eval ID → which reference file it most likely needs to evolve.
EVAL_TO_HANDLE = {
    "E-CAP-01": ("references/conviction-bar.md",
                 "Reviewer scores aren't predicting P&L; conviction-bar thresholds may be miscalibrated."),
    "E-CAP-02": ("references/falsification-playbook.md",
                 "Bad theses are getting through; falsifier set is incomplete."),
    "E-CAP-03": ("references/pr-format.md",
                 "Seeder hit-rate is low; thesis-seeding instructions need to be sharper."),
    "E-CAP-04": ("references/conviction-bar.md",
                 "Theses take too many iterations to MERGE; early gates too loose."),
    "E-CAP-05": ("references/falsification-playbook.md",
                 "Bad theses survive too many iterations before KILL; add earlier unconditional falsifiers."),
    "E-CAP-06": ("references/conviction-bar.md",
                 "Armed portfolio Sharpe below benchmark; arming gate is too generous."),
}

def latest_scores():
    files = sorted(SCORES.glob("*.json"))
    if not files: return None
    return json.loads(files[-1].read_text()), files[-1].stem

def worst_actionable_eval(scores):
    candidates = []
    for eid, r in scores.items():
        if eid not in EVAL_TO_HANDLE: continue
        if r.get("passing") is False:
            candidates.append((eid, r))
    if not candidates: return None
    # rank by how far below target
    def gap(item):
        eid, r = item
        s = r.get("score")
        tgt = r.get("target") or r.get("target_max") or 0
        return abs((s or 0) - tgt)
    candidates.sort(key=gap, reverse=True)
    return candidates[0]

def next_hpr_num():
    nums = [int(p.stem.split("-")[1]) for p in HARNESS.glob("HPR-*.md")]
    return (max(nums)+1) if nums else 1

def propose(dry_run=False):
    scores, week_tag = latest_scores() if latest_scores() else (None, None)
    if not scores:
        return {"action": "noop", "reason": "no eval scores yet — run scripts/run_evals.py first"}
    worst = worst_actionable_eval(scores)
    if not worst:
        return {"action": "noop", "reason": "all actionable evals passing"}
    eid, r = worst
    handle, rationale = EVAL_TO_HANDLE[eid]
    n = next_hpr_num()
    body = f"""# HPR-{n:03d}: Evolve {handle} based on {eid}

**Date**: {date.today().isoformat()}
**Triggered by**: {eid} ({r})
**Handle**: {handle}
**Rationale**: {rationale}

## Eval data
```json
{json.dumps(r, indent=2, default=str)}
```

## Proposed change
*To be filled in by reflective LLM subagent. This stub triggers a subagent call
that reads {handle}, examines the failure cases linked from the eval, and proposes
a textual diff. The diff is then shadow-evaluated against the last 5 PRs before
this HPR is finalized.*

## Shadow eval results
*Filled by `shadow_eval.py` after the proposed diff is generated. Required:
delta on {eid} ≥ +10%; lock-in test on prior 5 PRs must not degrade ≥ 1 point.*

## Approval
- [ ] User approves
- [ ] Lock-in test passes
- [ ] Apply diff to {handle}
- [ ] Commit to memory: "Remember that autoresearch evolved {handle} via HPR-{n:03d}"
"""
    if not dry_run:
        (HARNESS / f"HPR-{n:03d}.md").write_text(body)
    return {"action": "harness_pr_drafted", "eval": eid, "handle": handle,
            "hpr_path": str(HARNESS / f"HPR-{n:03d}.md")}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    print(json.dumps(propose(a.dry_run), indent=2))

if __name__ == "__main__": main()
