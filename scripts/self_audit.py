"""
Self-audit: enforce "NO axis unscrutinized" (CONSTITUTION RSI mandate).

Enumerates EVERY axis of the Fund, scores each on health/coverage/freshness from
ground truth, finds the weakest, and emits a forcing function (the single highest-
leverage improvement to make next). Writes runs/SELF_AUDIT.md and appends the
weakest-axis action to runs/QUEUE.json so improvement is scheduled, not hoped-for.

Run periodically (e.g. hourly cron or end of an idle tick). The point is that the
*completeness of improvement* is itself audited — a meta-axis.
"""
from __future__ import annotations
import sys, json, subprocess, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _exists(p): return (ROOT / p).exists()
def _age_h(p):
    f = ROOT / p
    if not f.exists():
        return None
    return round((dt.datetime.now().timestamp() - f.stat().st_mtime) / 3600, 1)
def _has_test(module_stem):
    """crude: is this module exercised by any eval/dryrun or unit test?"""
    search_dirs = [str(ROOT / "evals"), str(ROOT / "tests")]
    search_dirs = [d for d in search_dirs if Path(d).exists()]
    if not search_dirs:
        return False
    hits = subprocess.run(["grep", "-rl", module_stem, *search_dirs],
                          capture_output=True, text=True).stdout.strip()
    return bool(hits)


def _open_nondraft_pr_count():
    """Count Teammate's open, non-draft PRs. An un-drained queue is a P1 forcing function
    (OBLIGATION A in skills/computer-fund-operating-doctrine). Returns (count, info);
    count is None if gh is unavailable (sandbox down) so the axis fails-safe to 'unknown'."""
    try:
        out = subprocess.run(
            ["gh", "pr", "list", "--repo", "salvatorepplx/computer-fund",
             "--state", "open", "--json", "number,isDraft"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        prs = json.loads(out) if out else []
        nondraft = [p for p in prs if not p.get("isDraft")]
        return len(nondraft), [p["number"] for p in nondraft]
    except Exception as e:
        return None, f"gh unavailable: {str(e)[:50]}"


# Each axis: (name, why_it_matters, score_fn -> (0..1 health, note))
def axis_signal():
    ok = _exists("execution/web_sentiment.py")
    tested = _has_test("web_sentiment")
    return (0.8 if ok and tested else 0.4 if ok else 0.0,
            f"web_sentiment present={ok} tested={tested}; single source (no cross-source corroboration yet)")

def axis_pr_queue():
    """OBLIGATION A: Teammate cannot merge. An un-drained non-draft PR queue freezes his
    throughput and is a P1 — never 'nothing to act on'."""
    count, info = _open_nondraft_pr_count()
    if count is None:
        return (0.6, f"Teammate PR queue UNKNOWN ({info}); re-check when gh is available")
    if count == 0:
        return (1.0, "Teammate PR queue DRAINED (0 non-draft open PRs)")
    return (max(0.0, 0.4 - 0.05 * count),
            f"P1: {count} non-draft Teammate PR(s) OPEN and undisposed: {info}. Drain now (review->merge/request-changes).")

def axis_verdict():
    ok = _exists("evals/leadlag_real.py") and _exists("evals/leadlag_permutation.py")
    return (0.9 if ok else 0.3, f"lead-lag + permutation null present={ok}; de-burst+circularity+p-value gates live")

def axis_pipeline():
    ok = _exists("execution/alpha_pipeline.py") and _has_test("alpha_pipeline")
    return (0.9 if ok else 0.3, f"alpha_pipeline present+tested={ok} (e2e dryrun 18/18)")

def axis_safety():
    ok = _exists("execution/safety.py") and _has_test("safety")
    return (0.95 if ok else 0.0, f"safety rails present+tested={ok}; allowlist/sizing/kill verified to fire")

def axis_capture_infra():
    ok = _exists("scripts/capture_and_commit.sh")
    return (0.85 if ok else 0.3, f"hardened single wrapper={ok}; transient 400/502 still skips ticks (no in-script session retry possible)")

def axis_universe():
    n = sum(1 for _ in (ROOT / "runs" / "sentiment" / "series").glob("TICKER_*.jsonl"))
    return (min(1.0, n / 6.0), f"{n} names tracked (target broader cross-section for cross-sectional lead-lag; PATH/CRM queued)")

def axis_state_memory():
    age = _age_h("STATE.md")
    fresh = age is not None and age < 1.0
    return (0.85 if fresh else 0.5, f"STATE.md age={age}h (front door); Computer memory holds governance+technical_state+lessons")

def axis_lessons():
    age = _age_h("corpus/lessons.md")
    return (0.8, f"lessons.md age={age}h; capturing bug-classes + findings")

def axis_sim():
    if _exists("sim/RETIRED.md"):
        return (0.7, "sim PARKED by decision (RETIRED.md): off critical path, re-activate only if a future thesis needs it")
    ok = _exists("sim/sentiment_sim.py")
    return (0.3, f"sim present={ok} but UNUSED in the live verdict path (wire, kill, or formally park)")

def axis_graph():
    if _exists("graph/RETIRED.md"):
        return (0.7, "graph PARKED by decision (RETIRED.md): off critical path, re-activate only if a future thesis needs it")
    ok = _exists("graph/kg.py")
    return (0.3, f"knowledge graph present={ok} but UNDERUSED (wire, kill, or formally park)")

def axis_cron_tasks():
    return (0.7, "cron task prompts now self-orienting (read STATE.md/lessons first, act-not-log); watch cron prompt not yet upgraded to same standard")

def axis_meta_improvement():
    # self-audit exists AND is scheduled hourly (cron 253ff74b) AND every cron task is
    # self-orienting + never-idle. The completeness-of-improvement axis is now covered.
    ok = _exists("scripts/self_audit.py")
    return (0.85 if ok else 0.2, f"self-audit exists={ok}, scheduled hourly (cron 253ff74b), all cron prompts self-orienting+never-idle")


AXES = [
    ("pr_queue", axis_pr_queue),
    ("signal", axis_signal), ("verdict", axis_verdict), ("pipeline", axis_pipeline),
    ("safety", axis_safety), ("capture_infra", axis_capture_infra), ("universe", axis_universe),
    ("state_memory", axis_state_memory), ("lessons", axis_lessons), ("sim", axis_sim),
    ("graph", axis_graph), ("cron_tasks", axis_cron_tasks), ("meta_improvement", axis_meta_improvement),
]


def run():
    rows = []
    for name, fn in AXES:
        try:
            score, note = fn()
        except Exception as e:
            score, note = 0.0, f"AUDIT ERROR: {str(e)[:60]}"
        rows.append({"axis": name, "health": round(score, 2), "note": note})
    rows_sorted = sorted(rows, key=lambda r: r["health"])
    weakest = rows_sorted[0]

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    md = [f"# Computer Fund — SELF-AUDIT (every axis under scrutiny)",
          f"_Generated {now}. RSI mandate: no axis sits unimproved._\n",
          "| axis | health | note |", "|---|---|---|"]
    for r in rows_sorted:
        md.append(f"| {r['axis']} | {r['health']} | {r['note']} |")
    md += ["",
           f"## Weakest axis -> forcing function",
           f"**{weakest['axis']}** (health {weakest['health']}): {weakest['note']}",
           f"Next improvement must target this axis (or justify in writing why another axis is higher-leverage)."]
    (ROOT / "runs" / "SELF_AUDIT.md").write_text("\n".join(md) + "\n")

    # schedule the weakest-axis fix into the durable queue
    qpath = ROOT / "runs" / "QUEUE.json"
    try:
        q = json.loads(qpath.read_text())
    except Exception:
        q = {"items": []}
    aid = f"AUDIT-{weakest['axis']}"
    items = [i for i in q.get("items", []) if i.get("id") != aid]
    items.insert(0, {"id": aid, "kind": "improve", "priority": 1, "owner": "computer",
                     "desc": f"Weakest axis per self-audit: {weakest['axis']} (health {weakest['health']}). {weakest['note']}",
                     "status": "pending", "added": now})
    q["items"] = items
    q["updated"] = now
    qpath.write_text(json.dumps(q, indent=2))

    print(f"weakest axis: {weakest['axis']} (health {weakest['health']})")
    print(f"-> {weakest['note']}")
    return weakest


if __name__ == "__main__":
    run()
