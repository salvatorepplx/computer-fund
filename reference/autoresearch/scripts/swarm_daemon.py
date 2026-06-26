"""Always-on swarm daemon. Tops up workers every N seconds, never lets the pool drop below target.

Runs as a background nohup process. The hourly swarm coordinator cron now just
ensures this daemon is alive, restarting it if dead.

Usage:
    python swarm_daemon.py start --target 14 --interval 60
    python swarm_daemon.py stop
    python swarm_daemon.py status
    python swarm_daemon.py ensure_alive --target 14 --interval 60  # called by cron
"""
from __future__ import annotations
import argparse, json, os, signal, subprocess, sys, time
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
PIDFILE = ROOT / "evals" / "swarm" / ".daemon.pid"
LOGFILE = ROOT / "evals" / "swarm" / "daemon.log"
PIDFILE.parent.mkdir(parents=True, exist_ok=True)

def _is_alive(pid):
    try: os.kill(pid, 0); return True
    except Exception: return False

def status():
    if not PIDFILE.exists(): return {"running": False}
    try:
        pid = int(PIDFILE.read_text())
        if _is_alive(pid):
            return {"running": True, "pid": pid}
        PIDFILE.unlink(missing_ok=True)
        return {"running": False, "stale_removed": True}
    except Exception:
        PIDFILE.unlink(missing_ok=True)
        return {"running": False}

def start(target=14, interval=60):
    if status().get("running"): return {"already_running": True, "pid": status()["pid"]}
    pid = os.fork()
    if pid > 0:
        PIDFILE.write_text(str(pid))
        return {"started": True, "pid": pid, "target": target, "interval": interval}
    # child: detach
    os.setsid()
    with LOGFILE.open("a") as logf:
        logf.write(f"\n=== daemon started {datetime.now(timezone.utc).isoformat()} target={target} interval={interval}s ===\n"); logf.flush()
        try:
            while True:
                try:
                    subprocess.run([sys.executable, str(ROOT/"scripts"/"swarm.py"), "reap"],
                                   capture_output=True, timeout=15)
                    subprocess.run([sys.executable, str(ROOT/"scripts"/"swarm.py"), "topup",
                                    "--target", str(target)], capture_output=True, timeout=20)
                except Exception as e:
                    logf.write(f"[{datetime.now(timezone.utc).isoformat()}] err: {e}\n"); logf.flush()
                time.sleep(interval)
        except Exception as e:
            logf.write(f"[{datetime.now(timezone.utc).isoformat()}] daemon exit: {e}\n")
    sys.exit(0)

def stop():
    if not PIDFILE.exists(): return {"running": False}
    try:
        pid = int(PIDFILE.read_text())
        os.kill(pid, signal.SIGTERM)
        PIDFILE.unlink(missing_ok=True)
        return {"stopped": True, "pid": pid}
    except Exception as e:
        PIDFILE.unlink(missing_ok=True)
        return {"err": str(e)}

def ensure_alive(target=14, interval=60):
    s = status()
    if s.get("running"): return {"already_alive": True, "pid": s["pid"]}
    return start(target, interval)

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start"); st.add_argument("--target", type=int, default=14); st.add_argument("--interval", type=int, default=60)
    sub.add_parser("stop"); sub.add_parser("status")
    ea = sub.add_parser("ensure_alive"); ea.add_argument("--target", type=int, default=14); ea.add_argument("--interval", type=int, default=60)
    a = p.parse_args()
    if a.cmd == "start": print(json.dumps(start(a.target, a.interval), indent=2))
    elif a.cmd == "stop": print(json.dumps(stop(), indent=2))
    elif a.cmd == "status": print(json.dumps(status(), indent=2))
    elif a.cmd == "ensure_alive": print(json.dumps(ensure_alive(a.target, a.interval), indent=2))

if __name__ == "__main__": main()
