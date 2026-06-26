"""Infra factory — first-class loop that builds reusable software, not just theses.

Every wishlist item in infra/registry.json is a candidate "infra ticket." Every
recurring annoyance the iteration loop hits (e.g. "had to re-implement vol-targeting
again") is logged here and considered alongside theses for the next tick.

Usage:
    python infra_factory.py wishlist             # show the wishlist + open questions
    python infra_factory.py log_friction "..."   # log a friction point worth fixing
    python infra_factory.py next                 # propose the next infra build by ROI
    python infra_factory.py retire <script>      # mark a script retired in infra/RETIRED.md
"""
from __future__ import annotations
import argparse, csv, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INFRA = ROOT / "infra"
INFRA.mkdir(exist_ok=True)
REG = INFRA / "registry.json"
FRICTION = INFRA / "friction_log.csv"
RETIRED = INFRA / "RETIRED.md"

def _reg():
    return json.loads(REG.read_text()) if REG.exists() else {"scripts":{}, "wishlist":[]}

def wishlist():
    r = _reg()
    out = {
        "stance": r.get("stance"),
        "wishlist": r.get("wishlist", []),
        "open_questions_across_scripts": {
            name: meta.get("open_questions", [])
            for name, meta in r.get("scripts", {}).items()
            if meta.get("open_questions")
        }
    }
    return out

def log_friction(note):
    if not FRICTION.exists():
        with FRICTION.open("w", newline="") as f:
            csv.writer(f).writerow(["ts","note","status"])
    with FRICTION.open("a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc).isoformat(), note, "OPEN"])
    return {"logged": note}

def next_build():
    """Propose the next infra build, by frequency-of-friction × strategic-leverage.
    This is intentionally heuristic — the parent agent should reason about it.
    """
    r = _reg()
    frictions = []
    if FRICTION.exists():
        with FRICTION.open() as f:
            frictions = [row for row in csv.DictReader(f) if row.get("status") == "OPEN"]
    # group frictions by similarity (naive bag-of-keywords)
    by_topic = {}
    for fr in frictions:
        topic = fr["note"].split()[0].lower() if fr["note"] else "misc"
        by_topic.setdefault(topic, []).append(fr["note"])
    candidates = [{"source": "wishlist", "item": w} for w in r.get("wishlist", [])]
    candidates += [{"source": "friction", "topic": t, "count": len(v), "samples": v[:3]}
                   for t, v in by_topic.items() if len(v) >= 2]
    return {"candidates": candidates,
            "next_step": "Parent agent should pick the highest-leverage candidate; usually friction with count>=3 OR a wishlist item that unblocks multiple open questions."}

def retire(script_name, reason="No longer reachable from any active loop"):
    RETIRED.parent.mkdir(exist_ok=True)
    header = "# Retired Infrastructure\n\nProvisional record of scripts/modules that were used and then surpassed. Keeping this list visible matters — it's the negative space of the infra registry.\n\n" if not RETIRED.exists() else ""
    RETIRED.open("a").write(f"{header}- **{script_name}** · retired {datetime.now(timezone.utc).date().isoformat()} · {reason}\n")
    return {"retired": script_name, "reason": reason}

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("wishlist")
    lf = sub.add_parser("log_friction"); lf.add_argument("note")
    sub.add_parser("next")
    rt = sub.add_parser("retire"); rt.add_argument("script"); rt.add_argument("--reason", default="No longer reachable from any active loop")
    a = p.parse_args()
    if a.cmd == "wishlist": print(json.dumps(wishlist(), indent=2))
    elif a.cmd == "log_friction": print(json.dumps(log_friction(a.note), indent=2))
    elif a.cmd == "next": print(json.dumps(next_build(), indent=2))
    elif a.cmd == "retire": print(json.dumps(retire(a.script, a.reason), indent=2))

if __name__ == "__main__": main()
