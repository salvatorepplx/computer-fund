"""Thin wrapper that does the I/O scaffolding for a thesis iteration.

This script doesn't run the actual backtest reasoning — that requires an LLM
subagent. What it does:
  1. Acquire a lock on the thesis
  2. Prepare an "iteration packet" the cron subagent can consume:
     - latest PR path
     - thesis.md
     - data paths
     - the references it must obey
     - the exact follow-up commands to run after the backtest completes
  3. On success, emit a JSON blob the subagent uses
  4. On failure (lock not acquired / thesis missing), exit non-zero with reason

The cron subagent's flow is:
    python scripts/iterate.py prepare --thesis <id>   # returns packet
    ...subagent reads packet, does the actual backtest + falsifiers + PR write...
    python scripts/iterate.py finalize --thesis <id> --outcome arm|kill|iterate \
        --signal_axis <s> --universe_axis <u> --horizon_axis <h> --structure_axis <st> \
        [--p_value <p>] [--entry_px <px> --side long|short --size <usd> --stop <frac> --target <frac>]

Usage:
    python iterate.py prepare --thesis <id>
    python iterate.py finalize --thesis <id> --outcome arm --signal_axis price_momentum ...
    python iterate.py release --thesis <id>  # if subagent aborts before finalize
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"

def _latest_pr(tdir: Path) -> Path | None:
    prs = sorted((tdir / "prs").glob("PR-*.md")) if (tdir / "prs").exists() else []
    return prs[-1] if prs else None

def prepare(thesis):
    tdir = RUNS / thesis
    if not tdir.exists():
        return {"ok": False, "error": f"thesis dir not found: {tdir}"}
    # Acquire lock via direct subprocess (so we don't double-import contextmanager)
    res = subprocess.run([sys.executable, str(ROOT/"scripts"/"locks.py"), "acquire", "--thesis", thesis],
                         capture_output=True, text=True)
    if "true" not in res.stdout.lower():
        return {"ok": False, "error": "lock not acquired (another iterator may be working)", "stdout": res.stdout}

    latest_pr = _latest_pr(tdir)
    packet = {
        "ok": True,
        "thesis": thesis,
        "thesis_dir": str(tdir),
        "thesis_md": str(tdir / "thesis.md") if (tdir / "thesis.md").exists() else None,
        "latest_pr": str(latest_pr) if latest_pr else None,
        "status": (tdir / "STATUS").read_text().strip() if (tdir / "STATUS").exists() else "SEEDED",
        "next_pr_num": (int(latest_pr.stem.split("-")[1]) + 1) if latest_pr else 1,
        "data_dir": str(tdir / "data"),
        "results_dir": str(tdir / "results"),
        "must_read": [
            str(ROOT / "SKILL.md"),
            str(ROOT / "references" / "conviction-bar.md"),
            str(ROOT / "references" / "falsification-playbook.md"),
            str(ROOT / "references" / "pr-format.md"),
            str(ROOT / "references" / "hypothesis-space.md"),
        ],
        "data_registry": str(ROOT / "data" / "registry.json"),
        "memory_queries_for_agent_layer": {
            "note": "These are queries the AGENT executing this iteration should run via its built-in memory_search tool. They are NOT shell commands. If you are a shell context with no memory_search tool, skip this section — the in-thread agent will surface relevant context.",
            "queries": [
                "What thesis_ids has autoresearch merged or killed?",
                "What features or factors are known to have look-ahead leaks in autoresearch?",
            ],
        },
        "finalize_command_template": (
            f"python scripts/iterate.py finalize --thesis {thesis} "
            "--outcome <arm|kill|iterate> --signal_axis <s> --universe_axis <u> "
            "--horizon_axis <h> --structure_axis <st> [--p_value <p>]"
        ),
        "release_on_abort": f"python scripts/iterate.py release --thesis {thesis}",
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    # Save packet alongside the thesis for audit
    (tdir / ".iteration_packet.json").write_text(json.dumps(packet, indent=2))
    return packet

def finalize(args):
    thesis = args.thesis
    tdir = RUNS / thesis
    if not tdir.exists():
        return {"ok": False, "error": f"thesis dir not found: {tdir}"}

    # Update bandit arms
    if all([args.signal_axis, args.universe_axis, args.horizon_axis, args.structure_axis]):
        outcome_map = {"arm": "win", "kill": "loss", "iterate": "noop"}
        outcome = outcome_map.get(args.outcome, "noop")
        for axis, value in [("signal", args.signal_axis), ("universe", args.universe_axis),
                            ("horizon", args.horizon_axis), ("structure", args.structure_axis)]:
            subprocess.run([sys.executable, str(ROOT/"scripts"/"hypothesis_space.py"),
                            "update", "--axis", axis, "--value", value, "--outcome", outcome],
                           capture_output=True)

    # Log p-value for multiple-testing tracking
    if args.p_value is not None:
        subprocess.run([sys.executable, str(ROOT/"scripts"/"multiple_testing.py"),
                        "log", "--thesis", thesis, "--p", str(args.p_value),
                        "--decision", args.outcome], capture_output=True)

    # Update STATUS
    status_map = {"arm": "ARMED", "kill": "KILLED", "iterate": "ITERATING"}
    new_status = status_map.get(args.outcome)
    if new_status:
        (tdir / "STATUS").write_text(new_status)

    # If ARM, open paper position
    paper_result = None
    if args.outcome == "arm" and args.entry_px and args.side and args.size:
        # Get latest PR ref
        latest_pr = _latest_pr(tdir)
        pr_ref = latest_pr.stem if latest_pr else "PR-001"
        # Infer ticker from thesis name (very rough fallback)
        ticker = args.ticker or thesis.split("_")[-1].upper()
        res = subprocess.run([sys.executable, str(ROOT/"scripts"/"paper_engine.py"), "open",
                              "--thesis", thesis, "--pr_ref", pr_ref, "--ticker", ticker,
                              "--side", args.side, "--size", str(args.size),
                              "--entry", str(args.entry_px),
                              "--stop", str(args.stop or 0.92),
                              "--target", str(args.target or 1.15)],
                             capture_output=True, text=True)
        paper_result = res.stdout

    # Run meta-orchestrator hot update
    subprocess.run([sys.executable, str(ROOT/"scripts"/"meta_orchestrator.py"), "hot"],
                   capture_output=True)

    # Release the lock
    subprocess.run([sys.executable, str(ROOT/"scripts"/"locks.py"), "release", "--thesis", thesis],
                   capture_output=True)

    # Append to CHANGELOG
    cl = tdir / "CHANGELOG.md"
    if not cl.exists(): cl.write_text(f"# {thesis} — CHANGELOG\n\n")
    cl.open("a").write(f"- **{datetime.now(timezone.utc).date().isoformat()}** · {args.outcome.upper()} · finalized via iterate.py\n")

    return {"ok": True, "thesis": thesis, "new_status": new_status,
            "outcome": args.outcome, "paper_result": paper_result}

def release(thesis):
    res = subprocess.run([sys.executable, str(ROOT/"scripts"/"locks.py"),
                          "release", "--thesis", thesis], capture_output=True, text=True)
    return {"released": thesis, "lock_output": res.stdout.strip()}

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prepare"); pr.add_argument("--thesis", required=True)
    fi = sub.add_parser("finalize")
    fi.add_argument("--thesis", required=True)
    fi.add_argument("--outcome", required=True, choices=["arm","kill","iterate"])
    fi.add_argument("--signal_axis"); fi.add_argument("--universe_axis")
    fi.add_argument("--horizon_axis"); fi.add_argument("--structure_axis")
    fi.add_argument("--p_value", type=float, default=None)
    fi.add_argument("--ticker", default=None)
    fi.add_argument("--side", choices=["long","short"], default=None)
    fi.add_argument("--size", type=float, default=None)
    fi.add_argument("--entry_px", type=float, default=None)
    fi.add_argument("--stop", type=float, default=None)
    fi.add_argument("--target", type=float, default=None)
    rl = sub.add_parser("release"); rl.add_argument("--thesis", required=True)
    a = p.parse_args()
    if a.cmd == "prepare": print(json.dumps(prepare(a.thesis), indent=2))
    elif a.cmd == "finalize": print(json.dumps(finalize(a), indent=2))
    elif a.cmd == "release": print(json.dumps(release(a.thesis), indent=2))

if __name__ == "__main__": main()
