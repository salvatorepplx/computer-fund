"""Swarm coordinator — keeps a pool of background workers alive at all times.

Design: each "worker" is an independent shell process doing one piece of useful work.
The coordinator periodically inspects the worker pool, spawns new workers to top up,
reaps finished ones, logs reasoning, and exits. The pool persists between coordinator
invocations because workers are detached background processes.

This is how we get "10+ subagents working in parallel at all times" inside the
constraints of cron (1-hour minimum, no run_subagent at cron-time).

Work types the swarm handles:
- DEEP_ITERATE: drain SEEDED queue via deep_iterate.py
- SWEEP: historical sweep across one (calendar × universe) combination
- META_REASONING: continuous meta-orchestrator (hot + reasoning_log analysis)
- PROMOTE_SWEEP: turn sweep BH-survivors into SEEDED theses
- INFRA_BUILD: pick up a friction-log item and try to address it
- CRITIC: adversarial replay of an ARMED thesis (when one exists)

Usage:
    python swarm.py status              # show pool state + work backlog
    python swarm.py topup --target 10   # ensure at least N workers running
    python swarm.py reap                # remove finished worker records
    python swarm.py kill_all            # stop all workers (emergency)
"""
from __future__ import annotations
import argparse, json, os, signal, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SWARM_DIR = ROOT / "evals" / "swarm"
SWARM_DIR.mkdir(parents=True, exist_ok=True)
WORKER_DIR = SWARM_DIR / "workers"; WORKER_DIR.mkdir(exist_ok=True)
LOG_DIR = SWARM_DIR / "logs"; LOG_DIR.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "scripts"))
from reasoning_log import log as rlog
from _thesis_dirs import list_thesis_dirs

# ---------- Worker registry ----------

def _worker_file(wid): return WORKER_DIR / f"{wid}.json"

def _is_alive(pid):
    try: os.kill(pid, 0); return True
    except (ProcessLookupError, PermissionError): return False
    except Exception: return False

def list_workers():
    """Return a list of currently registered workers; mark dead ones."""
    out = []
    for wf in WORKER_DIR.glob("*.json"):
        try: meta = json.loads(wf.read_text())
        except Exception: continue
        meta["alive"] = _is_alive(meta.get("pid", 0))
        meta["age_min"] = round((time.time() - meta.get("started_at", time.time())) / 60, 1)
        out.append(meta)
    return out

def reap_dead():
    """Delete records of workers no longer running."""
    n = 0
    for w in list_workers():
        if not w["alive"]:
            _worker_file(w["id"]).unlink(missing_ok=True); n += 1
    return n

def spawn_worker(kind: str, args: list[str], description: str = "") -> dict:
    """Fork a background worker. Returns its metadata."""
    wid = f"{kind}_{int(time.time()*1000)}_{os.getpid()}"
    log_path = LOG_DIR / f"{wid}.log"
    cmd = [sys.executable] + args
    # Daemonize: setsid + redirect stdio to log file
    with log_path.open("a") as logf:
        logf.write(f"\n=== worker {wid} started {datetime.now(timezone.utc).isoformat()} ===\n")
        logf.write(f"cmd: {' '.join(cmd)}\n"); logf.flush()
        proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT,
                                start_new_session=True, cwd=str(ROOT))
    meta = {"id": wid, "kind": kind, "pid": proc.pid,
            "cmd": cmd, "log": str(log_path),
            "description": description,
            "started_at": time.time()}
    _worker_file(wid).write_text(json.dumps(meta, indent=2))
    rlog("swarm", "decision", f"spawned worker {wid}", f"kind={kind} pid={proc.pid}", description[:200])
    return meta

# ---------- Work selection (the brain) ----------

def find_seeded_thesis():
    """Pick a SEEDED thesis that isn't locked. Skip the ones currently being worked."""
    locked = set()
    try:
        from locks import list_locks
        locked = {l["thesis"] for l in list_locks() if not l.get("stale")}
    except Exception: pass
    # Also exclude theses that are being iterated by a live worker
    in_flight = {w.get("target_thesis") for w in list_workers() if w["alive"]}
    for tdir in list_thesis_dirs(ROOT / "runs"):
        st = (tdir / "STATUS").read_text().strip()
        if st == "SEEDED" and tdir.name not in locked and tdir.name not in in_flight:
            return tdir.name
    return None

def find_iterating_thesis():
    """Pick an ITERATING thesis worth refining. Older first."""
    locked = set()
    try:
        from locks import list_locks
        locked = {l["thesis"] for l in list_locks() if not l.get("stale")}
    except Exception: pass
    in_flight = {w.get("target_thesis") for w in list_workers() if w["alive"]}
    candidates = []
    for tdir in list_thesis_dirs(ROOT / "runs"):
        if (tdir / "STATUS").read_text().strip() != "ITERATING": continue
        if tdir.name in locked or tdir.name in in_flight: continue
        prs = sorted((tdir / "prs").glob("PR-*.md"))
        last_mt = prs[-1].stat().st_mtime if prs else 0
        candidates.append((last_mt, tdir.name))
    candidates.sort()
    return candidates[0][1] if candidates else None

# Sweep rotation (deterministic by hour)
SWEEP_PAIRS = [
    ("data/events/fomc_history.csv", "SPY,TLT,GLD,QQQ,IWM"),
    ("data/events/fomc_history.csv", "XLK,XLF,XLE,XLU,XLV,XLY,XLI,XLB,XLP,XLRE,XLC"),
    ("data/events/fomc_history.csv", "MTUM,QUAL,VLUE,USMV,SPLV"),
    ("data/events/fomc_history.csv", "NVDA,AVGO,AMD,ORCL,TSM,INTC,MU"),
    ("data/events/fomc_history.csv", "MSFT,GOOGL,META,AAPL,AMZN,NFLX,ADBE"),
    ("data/events/cpi_history.csv", "SPY,TLT,GLD,QQQ,IWM"),
    ("data/events/cpi_history.csv", "XLK,XLF,XLE,XLU,XLV,XLY"),
    ("data/events/cpi_history.csv", "MTUM,QUAL,VLUE,USMV"),
    ("data/events/cpi_history.csv", "NVDA,META,GOOGL,AAPL,MSFT"),
]
def pick_sweep_rotation():
    h = int(time.time() / 3600)
    return SWEEP_PAIRS[h % len(SWEEP_PAIRS)]

# ---------- Top-up algorithm ----------

WORK_PLAN = [
    # (worker_kind, max_parallel, picker_fn, args_builder)
    ("DEEP_ITERATE_SEEDED", 4, find_seeded_thesis,
     lambda t: ([str(ROOT/"scripts"/"deep_iterate.py"), "--thesis", t], f"deep iterate seeded thesis {t}")),
    ("DEEP_ITERATE_ITERATING", 3, find_iterating_thesis,
     lambda t: ([str(ROOT/"scripts"/"deep_iterate.py"), "--thesis", t], f"deep iterate stale ITERATING thesis {t}")),
    ("SWEEP", 2, pick_sweep_rotation,
     lambda pair: ([str(ROOT/"scripts"/"historical_sweep.py"),
                    "--event_calendar", pair[0], "--tickers", pair[1],
                    "--window_pre", "1", "--window_post", "5",
                    "--out", f"runs/SWEEPS/swarm_{int(time.time())}"],
                   f"sweep {Path(pair[0]).stem} × {pair[1][:30]}")),
    ("EXPLORE", 2, lambda: True,
     lambda _: ([str(ROOT/"scripts"/"explorer.py"), "explore", "--n", "1"],
                "sample new hypothesis from grammar")),
    ("META_HOT", 1, lambda: True,
     lambda _: ([str(ROOT/"scripts"/"meta_orchestrator.py"), "hot"],
                "meta-orchestrator hot pass + watchlist update")),
    ("PROMOTE_SWEEP", 1, lambda: True,
     lambda _: ([str(ROOT/"scripts"/"sweep_to_thesis.py")],
                "promote sweep BH-survivors to SEEDED theses")),
    ("WARM_CACHE", 1, lambda: True,
     lambda _: ([str(ROOT/"scripts"/"data_fetcher.py"), "warm"],
                "warm data cache")),
]

def topup(target=10):
    """Ensure we have ~target workers running. Each work_plan entry caps its kind."""
    workers = [w for w in list_workers() if w["alive"]]
    by_kind = {}
    for w in workers: by_kind[w["kind"]] = by_kind.get(w["kind"], 0) + 1
    spawned = []
    for kind, cap, picker, builder in WORK_PLAN:
        running = by_kind.get(kind, 0)
        if running >= cap: continue
        for _ in range(cap - running):
            target_obj = picker()
            if not target_obj: continue
            try:
                args, desc = builder(target_obj)
                meta = spawn_worker(kind, args, desc)
                # Track which thesis a worker is targeting (for dedup)
                if isinstance(target_obj, str) and kind.startswith("DEEP_ITERATE"):
                    meta["target_thesis"] = target_obj
                    _worker_file(meta["id"]).write_text(json.dumps(meta, indent=2))
                spawned.append({"kind": kind, "id": meta["id"], "target": target_obj})
                if len(spawned) + len(workers) >= target: break
            except Exception as e:
                rlog("swarm", "observation", f"spawn failed for {kind}", str(e))
        if len(spawned) + len(workers) >= target: break
    return {"spawned": spawned, "now_running": len([w for w in list_workers() if w["alive"]])}

# ---------- Status ----------

def status():
    workers = list_workers()
    alive = [w for w in workers if w["alive"]]
    by_kind = {}
    for w in alive: by_kind[w["kind"]] = by_kind.get(w["kind"], 0) + 1
    return {
        "now": datetime.now(timezone.utc).isoformat(),
        "total_alive": len(alive),
        "by_kind": by_kind,
        "workers": [{"id": w["id"], "kind": w["kind"], "age_min": w["age_min"],
                     "desc": w.get("description","")[:80]} for w in alive],
        "dead_records": len([w for w in workers if not w["alive"]]),
    }

def kill_all():
    n = 0
    for w in list_workers():
        if w["alive"]:
            try: os.kill(w["pid"], signal.SIGTERM); n += 1
            except Exception: pass
        _worker_file(w["id"]).unlink(missing_ok=True)
    rlog("swarm", "decision", f"killed all {n} workers", "Emergency stop or full restart.")
    return {"killed": n}

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    t = sub.add_parser("topup"); t.add_argument("--target", type=int, default=10)
    sub.add_parser("reap")
    sub.add_parser("kill_all")
    a = p.parse_args()
    if a.cmd == "status": print(json.dumps(status(), indent=2))
    elif a.cmd == "topup":
        reap_dead()
        print(json.dumps(topup(a.target), indent=2))
        print(json.dumps(status(), indent=2))
    elif a.cmd == "reap": print(json.dumps({"reaped": reap_dead()}, indent=2))
    elif a.cmd == "kill_all": print(json.dumps(kill_all(), indent=2))

if __name__ == "__main__": main()
