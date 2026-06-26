"""Continuous autoresearch orchestrator.

Stateless tick: reads disk + memory, picks one action, executes, exits.
Designed to be called from a cron (hourly) or directly.

Usage:
    python orchestrator.py tick         # do one action by priority
    python orchestrator.py status       # print queue + portfolio
    python orchestrator.py plan         # show what tick WOULD do, no side effects
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
CORPUS = ROOT / "corpus"
CORPUS.mkdir(exist_ok=True)
QUEUE_PATH = RUNS / "QUEUE.json"
BACKLOG = RUNS / "BACKLOG.md"

# Provisional priority order; the meta-orchestrator may propose reordering.
# 'cheap' actions: KILL_CHECK, EXPLORE (sample-only), MTM_ONLY — safe at high frequency
# 'heavy' actions: ITERATE, RE_FALSIFY, INFRA_BUILD — require subagent, drain queue
ACTIONS = ["KILL_CHECK", "EXPLORE", "ITERATE_STALE", "RE_FALSIFY_MERGED", "INFRA_BUILD", "MTM_ONLY"]
CHEAP_ACTIONS = {"KILL_CHECK", "EXPLORE", "MTM_ONLY"}

def _read_status(tdir: Path) -> str:
    s = tdir / "STATUS"
    return s.read_text().strip() if s.exists() else "SEEDED"

import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent))
from _thesis_dirs import is_thesis_dir, list_thesis_dirs

def _list_theses() -> list[dict]:
    out = []
    for tdir in list_thesis_dirs(RUNS):
        prs = sorted((tdir / "prs").glob("PR-*.md")) if (tdir / "prs").exists() else []
        last_pr = prs[-1] if prs else None
        last_mtime = datetime.fromtimestamp(last_pr.stat().st_mtime) if last_pr else None
        out.append({
            "id": tdir.name,
            "status": _read_status(tdir),
            "pr_count": len(prs),
            "last_pr_at": last_mtime.isoformat() if last_mtime else None,
            "days_since_last_pr": (datetime.now() - last_mtime).days if last_mtime else None,
        })
    return out

def plan_next_action(mode: str = "any") -> dict:
    """Pure planner. Returns the action that tick() would execute.

    mode='cheap'   → only return cheap actions (KILL_CHECK/EXPLORE/MTM_ONLY)
    mode='heavy'   → only return heavy actions (ITERATE/RE_FALSIFY/INFRA_BUILD)
    mode='any'     → full priority order (legacy)
    """
    theses = _list_theses()

    # 1. KILL_CHECK is always first (cheap)
    if mode in ("any", "cheap") and any(t["status"] in ("ARMED", "MERGED") for t in theses):
        marker = RUNS / ".last_kill_check"
        last = marker.stat().st_mtime if marker.exists() else 0
        if (datetime.now().timestamp() - last) > 1800:  # tightened to 30min
            return {"action": "KILL_CHECK", "reason": "30min kill-switch sweep"}

    # 2. Heavy actions — only in heavy or any mode; require an unlocked thesis
    if mode in ("any", "heavy"):
        try:
            from locks import list_locks
            locked = {l["thesis"] for l in list_locks() if not l.get("stale")}
        except Exception:
            locked = set()
        # 2a. Drain SEEDED queue first — unfilled stub PRs need iteration
        seeded_unlocked = [t for t in theses if t["status"] == "SEEDED" and t["id"] not in locked]
        if seeded_unlocked:
            return {"action": "ITERATE_STALE", "thesis": seeded_unlocked[0]["id"],
                    "reason": "draining SEEDED queue"}
        # 2b. Stale ARMED
        stale = [t for t in theses if t["status"] == "ARMED"
                 and (t["days_since_last_pr"] or 99) >= 5 and t["id"] not in locked]
        if stale:
            return {"action": "ITERATE_STALE", "thesis": stale[0]["id"],
                    "reason": f"ARMED for {stale[0]['days_since_last_pr']}d w/o new PR"}
        # 2c. Weekly re-falsify MERGED
        weekly = [t for t in theses if t["status"] == "MERGED"
                  and (t["days_since_last_pr"] or 99) >= 7 and t["id"] not in locked]
        if weekly:
            return {"action": "RE_FALSIFY_MERGED", "thesis": weekly[0]["id"],
                    "reason": "weekly falsification window"}
        if mode == "heavy":
            return {"action": "NOOP", "reason": "no heavy work available (all locked or no candidates)"}

    # 3. EXPLORE: sample new hypothesis from the grammar (cheap)
    if mode in ("any", "cheap"):
        not_iterated = [t for t in theses if t["status"] == "SEEDED" and (t["pr_count"] or 0) <= 1]
        # in cheap mode, always explore if queue is below ceiling
        ceiling = 50 if mode == "cheap" else 5
        if len(not_iterated) < ceiling:
            return {"action": "EXPLORE",
                    "reason": f"queue has {len(not_iterated)} unstarted seeds, ceiling {ceiling}"}

    # 4. INFRA_BUILD (heavy)
    if mode in ("any", "heavy"):
        fl = ROOT / "infra" / "friction_log.csv"
        if fl.exists():
            try:
                import csv as _csv
                with fl.open() as f:
                    open_frictions = [r for r in _csv.DictReader(f) if r.get("status") == "OPEN"]
                if len(open_frictions) >= 3:
                    return {"action": "INFRA_BUILD",
                            "reason": f"{len(open_frictions)} open friction items",
                            "sample": open_frictions[:3]}
            except Exception:
                pass

    # 5. MTM (cheap default)
    return {"action": "MTM_ONLY", "reason": "queue stocked, no friction backlog"}

def execute(action: dict) -> dict:
    """Execute the planned action. Returns a result dict."""
    a = action["action"]
    if a == "KILL_CHECK":
        subprocess.run([sys.executable, str(ROOT / "scripts" / "paper_engine.py"), "kill_check"], check=False)
        (RUNS / ".last_kill_check").touch()
        subprocess.run([sys.executable, str(ROOT / "scripts" / "paper_engine.py"), "mtm"], check=False)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "paper_engine.py"), "portfolio_summary"], check=False)
        return {"ok": True, "action": a}
    elif a == "MTM_ONLY":
        subprocess.run([sys.executable, str(ROOT / "scripts" / "paper_engine.py"), "mtm"], check=False)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "paper_engine.py"), "portfolio_summary"], check=False)
        return {"ok": True, "action": a}
    elif a == "EXPLORE":
        # Sample a new hypothesis and scaffold it — the iteration subagent fills it in.
        res = subprocess.run([sys.executable, str(ROOT/"scripts"/"explorer.py"), "explore"],
                             capture_output=True, text=True)
        return {"ok": res.returncode == 0, "action": a, "stdout": res.stdout[-500:]}
    elif a in ("ITERATE_STALE", "RE_FALSIFY_MERGED", "INFRA_BUILD"):
        # These require a subagent — the cron prompt itself will spawn it.
        return {"ok": True, "action": a, "needs_subagent": True,
                "context": action}
    return {"ok": False, "error": f"unknown action {a}"}

def status() -> dict:
    return {
        "theses": _list_theses(),
        "next_action": plan_next_action(),
    }

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tick"); t.add_argument("--mode", default="any", choices=["any","cheap","heavy"])
    pp = sub.add_parser("plan"); pp.add_argument("--mode", default="any", choices=["any","cheap","heavy"])
    sub.add_parser("status")
    a = p.parse_args()
    if a.cmd == "tick":
        plan = plan_next_action(mode=getattr(a, "mode", "any"))
        print(json.dumps(plan, indent=2))
        res = execute(plan)
        print(json.dumps(res, indent=2))
    elif a.cmd == "plan":
        print(json.dumps(plan_next_action(mode=getattr(a, "mode", "any")), indent=2))
    elif a.cmd == "status":
        print(json.dumps(status(), indent=2, default=str))

if __name__ == "__main__":
    main()
