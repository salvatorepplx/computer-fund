"""Daily notification budget. Coalesces low-priority notifications into a digest
so high-frequency crons don't spam the user.

Rules (current working hypothesis):
- Hard cap: 6 notifications per UTC day across the whole system
- Priority levels: critical (always fires), high (counts toward cap), low (coalesced into EOD digest)
- A KILL switch trigger or new MERGE is always critical
- An EXPLORE-only tick is always low

Usage:
    python notify_budget.py request --priority high --title "..." --body "..."
        → exits 0 with "GO" if budget allows, else "QUEUE"
    python notify_budget.py drain   # called by EOD job; returns coalesced digest text
    python notify_budget.py status
"""
from __future__ import annotations
import argparse, json
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTIFY_DIR = ROOT / "evals" / "notify"
NOTIFY_DIR.mkdir(parents=True, exist_ok=True)
CAPS = {"critical": 999, "high": 6, "low": 0}  # low always queues

def _today_file(suffix):
    return NOTIFY_DIR / f"{date.today().isoformat()}_{suffix}.jsonl"

def request(priority, title, body):
    sent_p = _today_file("sent")
    queued_p = _today_file("queued")
    sent_count = sum(1 for _ in sent_p.open()) if sent_p.exists() else 0
    payload = {"ts": datetime.now(timezone.utc).isoformat(), "priority": priority,
               "title": title, "body": body}
    cap = CAPS.get(priority, 0)
    if priority == "critical" or sent_count < cap:
        with sent_p.open("a") as f: f.write(json.dumps(payload) + "\n")
        return {"decision": "GO", "sent_today": sent_count + 1, "cap": cap}
    with queued_p.open("a") as f: f.write(json.dumps(payload) + "\n")
    return {"decision": "QUEUE", "sent_today": sent_count, "cap": cap}

def drain():
    qp = _today_file("queued")
    if not qp.exists(): return {"items": [], "digest": "_no queued items_"}
    items = [json.loads(l) for l in qp.open()]
    lines = [f"# Coalesced autoresearch updates · {date.today().isoformat()}", ""]
    for it in items:
        lines.append(f"- **{it['title']}** ({it['priority']}) · {it['body'][:200]}")
    return {"items": items, "digest": "\n".join(lines)}

def status():
    sent_p = _today_file("sent"); queued_p = _today_file("queued")
    return {"date": date.today().isoformat(),
            "sent": sum(1 for _ in sent_p.open()) if sent_p.exists() else 0,
            "queued": sum(1 for _ in queued_p.open()) if queued_p.exists() else 0,
            "caps": CAPS}

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("request"); r.add_argument("--priority", required=True, choices=["critical","high","low"])
    r.add_argument("--title", required=True); r.add_argument("--body", required=True)
    sub.add_parser("drain"); sub.add_parser("status")
    a = p.parse_args()
    if a.cmd == "request": print(json.dumps(request(a.priority, a.title, a.body), indent=2))
    elif a.cmd == "drain": print(json.dumps(drain(), indent=2))
    elif a.cmd == "status": print(json.dumps(status(), indent=2))

if __name__ == "__main__": main()
