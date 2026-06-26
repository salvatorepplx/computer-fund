"""Reasoning swarm spawn-plan builder.

Cron-fired agents call this to get a JSON plan listing which roles to spawn with
which objectives. The cron-fired agent then uses its `run_subagent` tool to spawn
each role in parallel.

This script is just the plan-builder — it doesn't itself have run_subagent.
It outputs the prompts; the cron agent does the spawning.

Usage:
    python reasoning_swarm.py plan          # generate today's spawn plan as JSON
    python reasoning_swarm.py summary       # show recent role activity
"""
from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROLES_DIR = ROOT / "agent_roles"
REASONING_DIR = ROOT / "reasoning"
REASONING_DIR.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT/"scripts"))
from reasoning_log import log as rlog

def load_roster():
    return json.loads((ROLES_DIR / "roster.json").read_text())

def load_role_manual(role: str) -> str:
    p = ROLES_DIR / f"{role}.md"
    if not p.exists(): return ""
    return p.read_text()

def recent_role_activity(role: str, hours=4):
    """Count how many outputs this role has produced in the last `hours`."""
    d = REASONING_DIR / role
    if not d.exists(): return 0
    cutoff = datetime.now(timezone.utc).timestamp() - hours*3600
    return sum(1 for f in d.glob("*.md") if f.stat().st_mtime >= cutoff)

def build_objective(role: str, role_meta: dict) -> str:
    """Build the full prompt for one role spawn. This is what gets passed to run_subagent."""
    manual = load_role_manual(role)
    return f"""You are a worker in the autoresearch reasoning swarm. Your role is **{role}**.

## CORE OPERATING DISPOSITION

Before anything else, internalize /home/user/workspace/autoresearch/references/ethos.md.
The five postures: massive drive to succeed, huge inferiority complex, whimsical
detachment, bias toward action, mass skepticism in yourself. Default to "I'm
probably wrong about this." Suspect yourself first.

## YOUR ROLE MANUAL

{manual}

## SYSTEM CONTEXT YOU CAN ASSUME

- All paths are relative to /home/user/workspace/autoresearch/ unless otherwise noted.
- You have shell, file, run_subagent (for recursive depth), web search, and memory tools.
- The reasoning log lives at evals/reasoning_log.jsonl — log there via
  `python scripts/reasoning_log.py log --source {role} --kind <observation|hypothesis|decision|retro> --fact "..." --hypothesis "..."`.
- The thesis pipeline state lives in runs/<thesis>/STATUS.
- The eval suite is scripts/run_evals.py.
- The meta-orchestrator is scripts/meta_orchestrator.py.

## DELIVERABLE LOCATION

Write your output to: {role_meta.get("deliverable_dir", f"reasoning/{role}/")}<ISO_TIMESTAMP>.md

Then log a one-line reasoning_log entry summarizing what you did and why.

## YOUR RUNTIME BUDGET

You have up to {role_meta.get("max_runtime_min", 30)} minutes. Use it. Reading and
re-derivation are part of the work, not overhead. A 5-minute answer is almost
always worse than a 25-minute answer.

## FINAL REMINDER

Before submitting your deliverable, ask yourself: "If I had to bet $1000 that
every claim in this output is correct, would I refund any of it?" If yes, fix
those claims first.

Now do the work.
"""

def plan(tick_ts=None):
    """Build the spawn plan for one swarm tick."""
    roster = load_roster()
    tick_ts = tick_ts or datetime.now(timezone.utc).isoformat()
    spawns = []
    for role, meta in roster["roles"].items():
        freq = meta.get("frequency_per_swarm_tick", 1)
        for i in range(freq):
            obj = build_objective(role, meta)
            spawns.append({
                "role": role,
                "instance": i,
                "model": meta.get("model", "claude_opus_4_7"),
                "user_description": f"reasoning swarm: {role} #{i}",
                "task_name": f"swarm-{role}-{i}",
                "objective": obj,
            })
    return {
        "tick_ts": tick_ts,
        "n_spawns": len(spawns),
        "spawns": spawns,
        "note": "Cron-fired agent should iterate over `spawns` and call run_subagent for each. They run in parallel; await all via wait_for_subagents at the end.",
    }

def summary(hours=4):
    roster = load_roster()
    out = {"window_hours": hours, "by_role": {}}
    for role in roster["roles"]:
        out["by_role"][role] = recent_role_activity(role, hours)
    out["total_outputs"] = sum(out["by_role"].values())
    return out

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    s = sub.add_parser("summary"); s.add_argument("--hours", type=int, default=4)
    a = p.parse_args()
    if a.cmd == "plan":
        # Don't print the full objectives — too big. Print metadata + write full plan to disk.
        pl = plan()
        out_path = REASONING_DIR / f".latest_plan_{int(datetime.now(timezone.utc).timestamp())}.json"
        out_path.write_text(json.dumps(pl, indent=2))
        rlog("reasoning_swarm", "decision", f"plan built with {pl['n_spawns']} spawns",
             f"plan written to {out_path}", "cron agent should read this and spawn")
        # Print a compact summary so cron agent can see + the path to the full plan
        summary_view = {
            "tick_ts": pl["tick_ts"], "n_spawns": pl["n_spawns"],
            "plan_path": str(out_path),
            "roles_to_spawn": [{"role": s["role"], "instance": s["instance"],
                                "model": s["model"], "task_name": s["task_name"]}
                               for s in pl["spawns"]],
        }
        print(json.dumps(summary_view, indent=2))
    elif a.cmd == "summary":
        print(json.dumps(summary(a.hours), indent=2))

if __name__ == "__main__": main()
