"""Session-resident continuous explorer.

A long-running background process that fires cheap ticks every N minutes,
bypassing the 1-hour cron floor. Useful when the user wants peak throughput
during an active session.

Usage:
    python continuous.py start --interval 60      # tick every 60s
    python continuous.py start --interval 300     # tick every 5min
    python continuous.py stop                     # signal via PID file
    python continuous.py status

This is intentionally a separate concept from cron: cron is durable across
sessions but minimum 1h; this is fast but lives only as long as the process.
"""
from __future__ import annotations
import argparse, json, os, signal, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIDFILE = ROOT / "evals" / ".continuous.pid"
LOGFILE = ROOT / "evals" / "continuous.log"

def start(interval=60):
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text())
            os.kill(pid, 0)
            return {"already_running": True, "pid": pid}
        except (ProcessLookupError, ValueError):
            PIDFILE.unlink(missing_ok=True)
    # daemonize via double-fork-ish using nohup-style
    pid = os.fork()
    if pid > 0:
        PIDFILE.write_text(str(pid))
        return {"started": True, "pid": pid, "interval": interval, "log": str(LOGFILE)}
    # child — run the loop
    os.setsid()
    with LOGFILE.open("a") as log:
        log.write(f"[{datetime.now(timezone.utc).isoformat()}] continuous started, interval={interval}s\n")
        log.flush()
        try:
            while True:
                try:
                    res = subprocess.run(
                        [sys.executable, str(ROOT/"scripts"/"orchestrator.py"), "tick", "--mode", "cheap"],
                        capture_output=True, text=True, timeout=30
                    )
                    log.write(f"[{datetime.now(timezone.utc).isoformat()}] tick: {res.stdout[:200]}\n")
                    log.flush()
                except Exception as e:
                    log.write(f"[{datetime.now(timezone.utc).isoformat()}] tick error: {e}\n")
                    log.flush()
                time.sleep(interval)
        except KeyboardInterrupt:
            log.write(f"[{datetime.now(timezone.utc).isoformat()}] continuous stopped\n")
    sys.exit(0)

def stop():
    if not PIDFILE.exists(): return {"running": False}
    try:
        pid = int(PIDFILE.read_text())
        os.kill(pid, signal.SIGTERM)
        PIDFILE.unlink(missing_ok=True)
        return {"stopped": True, "pid": pid}
    except ProcessLookupError:
        PIDFILE.unlink(missing_ok=True)
        return {"already_stopped": True}

def status():
    if not PIDFILE.exists(): return {"running": False}
    try:
        pid = int(PIDFILE.read_text())
        os.kill(pid, 0)
        return {"running": True, "pid": pid, "log_tail": _tail(LOGFILE, 5)}
    except (ProcessLookupError, ValueError):
        PIDFILE.unlink(missing_ok=True)
        return {"running": False, "stale_pid_file_removed": True}

def _tail(p, n):
    if not p.exists(): return []
    lines = p.read_text().splitlines()
    return lines[-n:]

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("--interval", type=int, default=60)
    sub.add_parser("stop"); sub.add_parser("status")
    a = p.parse_args()
    if a.cmd == "start": print(json.dumps(start(a.interval), indent=2))
    elif a.cmd == "stop": print(json.dumps(stop(), indent=2))
    elif a.cmd == "status": print(json.dumps(status(), indent=2))

if __name__ == "__main__": main()
