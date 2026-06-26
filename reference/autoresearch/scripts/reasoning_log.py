"""Reasoning log — every script emits brief 'here's what just happened AND
what it means for the system' entries here. The meta-orchestrator and the
weekly deep-eval read this as their primary signal.

Reasoning is the execution. Treating it as a first-class artifact prevents the
'cron runs but no one knows why' pattern.

Entry shape: {ts, source, kind, fact, hypothesis, next_step}
- source: which script/cron emitted this
- kind: observation | hypothesis | decision | retro
- fact: what was observed
- hypothesis: what we think it means (1-2 sentences)
- next_step: a concrete thing this implies (optional)

Usage from scripts:
    from reasoning_log import log
    log(source="backtest_runner", kind="observation",
        fact="thesis X verdict=iterate (sharpe n/a, no signal data)",
        hypothesis="The signal stub is unimplemented; this thesis ID is uninformative.",
        next_step="Skip this signal family in sampler until implemented.")

Or from shell:
    python reasoning_log.py log --source x --kind observation --fact "..." --hypothesis "..."
"""
from __future__ import annotations
import argparse, csv, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "evals" / "reasoning_log.jsonl"
LOG.parent.mkdir(exist_ok=True)

KINDS = {"observation", "hypothesis", "decision", "retro", "friction"}

def log(source: str, kind: str, fact: str, hypothesis: str = "",
        next_step: str = "", payload: dict | None = None):
    """Append one reasoning entry. Always returns the written dict so callers can chain."""
    if kind not in KINDS: kind = "observation"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source, "kind": kind,
        "fact": fact[:1000], "hypothesis": hypothesis[:1000],
        "next_step": next_step[:500],
    }
    if payload: entry["payload"] = payload
    with LOG.open("a") as f: f.write(json.dumps(entry) + "\n")
    return entry

def tail(n=20, source=None, kind=None):
    if not LOG.exists(): return []
    lines = LOG.read_text().splitlines()
    out = []
    for l in reversed(lines):
        try: e = json.loads(l)
        except json.JSONDecodeError: continue
        if source and e.get("source") != source: continue
        if kind and e.get("kind") != kind: continue
        out.append(e)
        if len(out) >= n: break
    return list(reversed(out))

def summary(window_hours=24):
    """Roll up reasoning by source/kind for the past N hours."""
    if not LOG.exists(): return {"by_source": {}, "by_kind": {}, "total": 0}
    cutoff = datetime.now(timezone.utc).timestamp() - window_hours*3600
    by_src = {}; by_kind = {}; total = 0
    for l in LOG.read_text().splitlines():
        try: e = json.loads(l)
        except json.JSONDecodeError: continue
        try: ts = datetime.fromisoformat(e["ts"].replace("Z","+00:00")).timestamp()
        except Exception: continue
        if ts < cutoff: continue
        total += 1
        src = e.get("source", "unknown")
        kind = e.get("kind", "observation")
        by_src[src] = by_src.get(src, 0) + 1
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {"window_hours": window_hours, "total": total,
            "by_source": by_src, "by_kind": by_kind}

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    lg = sub.add_parser("log")
    lg.add_argument("--source", required=True); lg.add_argument("--kind", required=True)
    lg.add_argument("--fact", required=True); lg.add_argument("--hypothesis", default="")
    lg.add_argument("--next_step", default="")
    t = sub.add_parser("tail"); t.add_argument("--n", type=int, default=20)
    t.add_argument("--source", default=None); t.add_argument("--kind", default=None)
    s = sub.add_parser("summary"); s.add_argument("--hours", type=int, default=24)
    a = p.parse_args()
    if a.cmd == "log": print(json.dumps(log(a.source, a.kind, a.fact, a.hypothesis, a.next_step), indent=2))
    elif a.cmd == "tail": print(json.dumps(tail(a.n, a.source, a.kind), indent=2))
    elif a.cmd == "summary": print(json.dumps(summary(a.hours), indent=2))

if __name__ == "__main__": main()
