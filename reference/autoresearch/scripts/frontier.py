"""Maintain evals/frontier.json — the current set of (signal, universe, horizon, structure)
tuples that have produced surviving theses.

Read from bandit_arms.json (posterior means) + STATUS files (which arms produced ARMED/MERGED).
Write a compact JSON the meta-orchestrator and sweep cron can consume.

Usage:
    python frontier.py update              # refresh frontier.json
    python frontier.py show
"""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
from _thesis_dirs import list_thesis_dirs
RUNS = ROOT / "runs"
EVALS = ROOT / "evals"
EVALS.mkdir(exist_ok=True)
FRONTIER = EVALS / "frontier.json"
ARMS = EVALS / "bandit_arms.json"

def update():
    arms_state = json.loads(ARMS.read_text()) if ARMS.exists() else {"arms": {}}
    arms = arms_state.get("arms", {})

    # Per-axis posterior means
    by_axis = {}
    for k, v in arms.items():
        axis, val = k.split("::", 1)
        mean = v["a"] / (v["a"] + v["b"])
        n = v["a"] + v["b"] - 2  # observations
        by_axis.setdefault(axis, []).append({"value": val, "posterior_mean": mean, "n": n,
                                             "wins": v["a"]-1, "losses": v["b"]-1})
    for axis in by_axis:
        by_axis[axis].sort(key=lambda r: -r["posterior_mean"])

    # Surviving theses (ARMED or MERGED)
    surviving = []
    for tdir in list_thesis_dirs(RUNS):
        st = (tdir / "STATUS").read_text().strip() if (tdir / "STATUS").exists() else None
        if st in ("ARMED","MERGED"):
            surviving.append({"thesis": tdir.name, "status": st})

    frontier = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "posteriors_by_axis": by_axis,
        "surviving_theses": surviving,
        "note": "Top values per axis are the current 'frontier' — feature/universe/horizon/structure combos with highest posterior win-rate. The overnight sweep cron should bias new historical replays toward these.",
    }
    FRONTIER.write_text(json.dumps(frontier, indent=2))
    return frontier

def show():
    if not FRONTIER.exists(): return {"error": "frontier.json not yet built — run update first"}
    return json.loads(FRONTIER.read_text())

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("update"); sub.add_parser("show")
    a = p.parse_args()
    if a.cmd == "update": print(json.dumps(update(), indent=2))
    elif a.cmd == "show": print(json.dumps(show(), indent=2))

if __name__ == "__main__": main()
