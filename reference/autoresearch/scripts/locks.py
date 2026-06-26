"""File-based per-thesis locking for concurrent tick safety.

Lightweight: a lockfile at runs/<thesis_id>/.lock with the holder's pid/timestamp.
Stale locks (>10min) are reclaimable. No external dependency.

Usage:
    with acquire("thesis_id") as held:
        if held: ...do work...

Or:
    python locks.py acquire --thesis <id>
    python locks.py release --thesis <id>
    python locks.py list
"""
from __future__ import annotations
import argparse, json, os, time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
STALE_SECS = 600  # 10 minutes

def _lockpath(thesis_id): return RUNS / thesis_id / ".lock"

def _is_stale(p):
    try: return (time.time() - p.stat().st_mtime) > STALE_SECS
    except FileNotFoundError: return True

@contextmanager
def acquire(thesis_id, holder=None):
    lp = _lockpath(thesis_id)
    lp.parent.mkdir(parents=True, exist_ok=True)
    held = False
    try:
        if lp.exists() and not _is_stale(lp):
            yield False; return
        if lp.exists() and _is_stale(lp):
            lp.unlink(missing_ok=True)
        # exclusive create
        try:
            with open(lp, "x") as f:
                json.dump({"holder": holder or f"pid:{os.getpid()}", "ts": time.time()}, f)
            held = True
            yield True
        except FileExistsError:
            yield False
    finally:
        if held: lp.unlink(missing_ok=True)

def list_locks():
    out = []
    for tdir in RUNS.iterdir():
        if not tdir.is_dir(): continue
        lp = tdir / ".lock"
        if lp.exists():
            stale = _is_stale(lp)
            try: meta = json.loads(lp.read_text())
            except Exception: meta = {}
            out.append({"thesis": tdir.name, "stale": stale, **meta})
    return out

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("acquire"); a.add_argument("--thesis", required=True)
    r = sub.add_parser("release"); r.add_argument("--thesis", required=True)
    sub.add_parser("list")
    args = p.parse_args()
    if args.cmd == "acquire":
        with acquire(args.thesis) as held:
            print(json.dumps({"acquired": held}))
    elif args.cmd == "release":
        _lockpath(args.thesis).unlink(missing_ok=True); print(json.dumps({"released": args.thesis}))
    elif args.cmd == "list":
        print(json.dumps(list_locks(), indent=2))

if __name__ == "__main__": main()
