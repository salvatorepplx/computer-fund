"""Meta-orchestrator: reasoning layer over the entire autoresearch harness.

Runs in two modes:
- hot (after every iteration): cheap watchlist update
- deep (weekly): full reasoning pass that drafts a Harness PR

This script collects inputs and stages the prompt for a reasoning subagent.
The actual reasoning happens in the subagent (in the parent agent's tool-call layer).

Usage:
    python meta_orchestrator.py hot      # quick watchlist update
    python meta_orchestrator.py deep     # full reasoning, drafts HPR stub
    python meta_orchestrator.py status   # show current bottleneck candidates
"""
from __future__ import annotations
import argparse, csv, json, subprocess, sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
from _thesis_dirs import list_thesis_dirs
EVALS = ROOT / "evals"
SCORES = EVALS / "scores"
RUNS = ROOT / "runs"
WATCHLIST = EVALS / "watchlist.json"
META_LOG = EVALS / "meta_log.csv"
HARNESS = ROOT / "references" / "HARNESS-PRS"
HARNESS.mkdir(parents=True, exist_ok=True)

# Maps each eval to the harness component it most directly stresses.
EVAL_TO_COMPONENT = {
    "E-CAP-01": "reviewer_prompt",
    "E-CAP-02": "falsifier_set",
    "E-CAP-03": "seeder_prompt",
    "E-CAP-04": "conviction_bar",
    "E-CAP-05": "falsifier_set",
    "E-CAP-06": "conviction_bar",
    "E-REG-02": "falsifier_set",
    "E-REG-03": "pr_format",
    "E-REG-04": "conviction_bar",
    "E-REG-05": "process_hygiene",
}

COMPONENT_FILE = {
    "reviewer_prompt": "(embedded in iteration subagent prompts — update SKILL.md§iteration)",
    "falsifier_set": "references/falsification-playbook.md",
    "seeder_prompt": "(embedded in catalyst-scan cron task)",
    "conviction_bar": "references/conviction-bar.md",
    "pr_format": "references/pr-format.md",
    "catalyst_corpus": "corpus/catalysts.md",
    "lessons": "corpus/lessons.md",
    "action_budget": "references/continuous-loop.md",
    "kill_switches": "scripts/paper_engine.py",
    "eval_coverage": "evals/registry.json",
    "process_hygiene": "SKILL.md",
}

def _ensure_files():
    if not META_LOG.exists():
        with META_LOG.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp","mode","binding_component","evidence_eval",
                        "hpr_path","action","notes"])
    if not WATCHLIST.exists():
        WATCHLIST.write_text(json.dumps({"flags": [], "updated_at": None}, indent=2))

def latest_scores():
    files = sorted(SCORES.glob("*.json"))
    if not files: return None, None
    return json.loads(files[-1].read_text()), files[-1].stem

def score_history(n_weeks=4):
    files = sorted(SCORES.glob("*.json"))[-n_weeks:]
    return [(p.stem, json.loads(p.read_text())) for p in files]

def failing_evals(scores):
    out = []
    for eid, r in scores.items():
        if r.get("passing") is False:
            out.append((eid, r))
    return out

def collect_inputs():
    """Gather everything a reasoning subagent will need."""
    scores, week = latest_scores()
    history = score_history()
    failing = failing_evals(scores) if scores else []
    # PR list from last 7 days
    recent_prs = []
    cutoff = datetime.now().timestamp() - 7*24*3600
    for tdir in list_thesis_dirs(RUNS):
        for pr in (tdir / "prs").glob("PR-*.md") if (tdir / "prs").exists() else []:
            if pr.stat().st_mtime >= cutoff:
                recent_prs.append({"thesis": tdir.name, "pr": pr.name,
                                   "mtime": datetime.fromtimestamp(pr.stat().st_mtime).isoformat()})
    # Previous HPRs
    prior_hprs = sorted(HARNESS.glob("HPR-*.md"))
    # Component aggregation: how many failing evals map to each component?
    by_comp = {}
    for eid, r in failing:
        comp = EVAL_TO_COMPONENT.get(eid, "unknown")
        by_comp.setdefault(comp, []).append({"eval": eid, "score": r})
    return {
        "week": week,
        "scores": scores,
        "history_weeks": [w for w, _ in history],
        "failing_evals": failing,
        "failing_by_component": by_comp,
        "recent_prs": recent_prs,
        "prior_hprs": [p.name for p in prior_hprs],
    }

def hot():
    """Quick watchlist update. Append a flag if any new failure since last run."""
    _ensure_files()
    inputs = collect_inputs()
    wl = json.loads(WATCHLIST.read_text())
    new_flags = []
    for comp, evs in inputs["failing_by_component"].items():
        new_flags.append({
            "ts": datetime.now().isoformat(),
            "component": comp,
            "file": COMPONENT_FILE.get(comp, "?"),
            "evals": [e["eval"] for e in evs],
        })
    wl["flags"] = (wl.get("flags", []) + new_flags)[-50:]
    wl["updated_at"] = datetime.now().isoformat()
    WATCHLIST.write_text(json.dumps(wl, indent=2))
    print(json.dumps({"mode": "hot", "new_flags": len(new_flags),
                      "components": list(inputs["failing_by_component"].keys())}, indent=2))

def next_hpr_num():
    nums = [int(p.stem.split("-")[1]) for p in HARNESS.glob("HPR-*.md")]
    return (max(nums)+1) if nums else 1

def deep():
    """Full reasoning pass: stages the structured prompt for a reasoning subagent.

    Writes a stub HPR file and prints the prompt that the parent agent should
    feed to a fresh-context reasoning subagent. The subagent fills in the diagnosis
    fields and saves the completed HPR.
    """
    _ensure_files()
    # 1. Run full eval suite first
    subprocess.run([sys.executable, str(ROOT/"scripts"/"run_evals.py")], check=False)
    inputs = collect_inputs()
    n = next_hpr_num()

    # Pick top candidate by # of failing evals + watchlist density
    wl = json.loads(WATCHLIST.read_text()).get("flags", [])
    comp_counts = {}
    for f in wl[-30:]:
        comp_counts[f["component"]] = comp_counts.get(f["component"], 0) + 1
    for comp, evs in inputs["failing_by_component"].items():
        comp_counts[comp] = comp_counts.get(comp, 0) + 3*len(evs)
    if not comp_counts:
        print(json.dumps({"action": "NOOP", "reason": "no failing evals or watchlist signals"}))
        return
    binding = max(comp_counts, key=comp_counts.get)
    target_file = COMPONENT_FILE.get(binding, "?")

    # 2. Write HPR stub with structured fields the reasoning subagent must fill
    hpr_path = HARNESS / f"HPR-{n:03d}.md"
    stub = f"""# HPR-{n:03d}: Meta-orchestrator diagnosis — {binding}

**Date**: {date.today().isoformat()}
**Mode**: deep
**Binding component (preliminary)**: {binding}
**Target file**: {target_file}
**Component scoring**:
```json
{json.dumps(comp_counts, indent=2)}
```

## Inputs gathered
```json
{json.dumps({k: v for k, v in inputs.items() if k != "scores"}, indent=2, default=str)}
```

## Latest eval scores (excerpt)
```json
{json.dumps(inputs["scores"], indent=2, default=str)}
```

---

## REASONING SUBAGENT — fill in below this line

### bottleneck_diagnosis
- **binding_component**: {binding}
- **evidence — primary**: <which eval(s)>
- **evidence — corroborating**: <which PRs / paper outcomes>
- **counter_evidence**: <what would argue against this>
- **why_now**: <why THIS cycle, not last cycle>

### proposed_change
- **file**: {target_file}
- **smallest_change** (1-2 sentences): <intent>
- **expected_eval_delta — primary**: <which eval, by how much>
- **expected_eval_delta — risk**: <which eval could regress>
- **reversibility**: <how easy to roll back>
- **draft diff** (full proposed text replacement, marked-up):

```
<insert proposed text changes here>
```

### shadow_eval_design
- **replay_set**: <list of 5 prior PR paths>
- **must_not_regress**: <list of evals that must stay within ±1 of baseline>
- **promote_threshold**: <numeric delta needed on primary eval>

### alternative_considered
- **next_best_bottleneck**: <runner-up>
- **why_deferred**: <one line>

### self_check (MUST be answered honestly; do not skip)
- **am_i_chasing_noise**: <yes/no + reasoning>
- **is_this_just_overfitting_to_the_last_pr**: <yes/no + reasoning>
- **would_a_fresh_reviewer_agree**: <yes/no + reasoning>

### Verdict
**ACTION**: PROPOSE_HPR | NOOP_WATCHLIST | NOOP_INSUFFICIENT_DATA
**RATIONALE**: <one paragraph>
"""
    hpr_path.write_text(stub)

    # 3. Log to meta_log
    with META_LOG.open("a", newline="") as f:
        w = csv.writer(f)
        w.writerow([datetime.now().isoformat(), "deep", binding,
                    ",".join(sorted(set(eid for eid, _ in inputs["failing_evals"]))),
                    str(hpr_path), "STUB_DRAFTED", f"top_comp_score={comp_counts.get(binding)}"])

    print(json.dumps({"action": "STUB_DRAFTED", "binding": binding,
                      "hpr_path": str(hpr_path), "next_step":
                      "Parent agent should spawn a reasoning subagent with this HPR file as input."},
                     indent=2))

def status():
    _ensure_files()
    inputs = collect_inputs()
    wl = json.loads(WATCHLIST.read_text())
    print(json.dumps({
        "latest_week": inputs["week"],
        "failing_evals": [eid for eid, _ in inputs["failing_evals"]],
        "failing_by_component": list(inputs["failing_by_component"].keys()),
        "watchlist_flags_30d": len(wl.get("flags", [])),
        "prior_hprs": inputs["prior_hprs"],
    }, indent=2))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["hot","deep","status"])
    a = p.parse_args()
    {"hot": hot, "deep": deep, "status": status}[a.mode]()

if __name__ == "__main__": main()
