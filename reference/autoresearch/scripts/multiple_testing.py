"""Benjamini-Hochberg FDR correction + family tracking.

Every hypothesis the system tests is logged in evals/htest_log.csv with:
  thesis_id, family_week, raw_p, decision_before_bh

This script applies BH correction at the weekly-family level and updates
each row's `bh_pass` boolean. A thesis cannot MERGE without bh_pass=True.

Usage:
    python multiple_testing.py log --thesis H_xxx --p 0.01 --family 2026-W21 --decision passed
    python multiple_testing.py recompute            # re-apply BH across all weeks
    python multiple_testing.py status               # show families + pass rates
"""
from __future__ import annotations
import argparse, csv, json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
LOG = EVALS / "htest_log.csv"
COLS = ["thesis_id","family_week","raw_p","decision_before_bh","bh_pass","bh_q"]
FDR = 0.05  # default family-wise FDR

def _read():
    if not LOG.exists(): return []
    with LOG.open() as f: return list(csv.DictReader(f))

def _write(rows):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader()
        for r in rows: w.writerow({c: r.get(c,"") for c in COLS})

def log(thesis_id, raw_p, family_week=None, decision="unknown"):
    rows = _read()
    fw = family_week or date.today().strftime("%Y-W%V")
    rows.append({"thesis_id": thesis_id, "family_week": fw,
                 "raw_p": f"{float(raw_p):.6f}", "decision_before_bh": decision,
                 "bh_pass": "", "bh_q": ""})
    _write(rows)
    recompute()  # re-apply BH after every new entry
    return {"logged": thesis_id, "family": fw, "p": raw_p}

def recompute():
    rows = _read()
    by_family = {}
    for r in rows: by_family.setdefault(r["family_week"], []).append(r)
    for fw, group in by_family.items():
        sorted_g = sorted(group, key=lambda r: float(r["raw_p"]))
        m = len(sorted_g)
        for i, r in enumerate(sorted_g, start=1):
            q = float(r["raw_p"]) * m / i
            r["bh_q"] = f"{q:.6f}"
            r["bh_pass"] = "True" if q <= FDR else "False"
    # flatten back, preserving order
    all_rows = []
    for fw in sorted(by_family):
        all_rows.extend(by_family[fw])
    _write(all_rows)
    return {"families": len(by_family), "total_tested": sum(len(g) for g in by_family.values())}

def status():
    rows = _read()
    by_family = {}
    for r in rows: by_family.setdefault(r["family_week"], []).append(r)
    out = {"families": []}
    for fw in sorted(by_family):
        g = by_family[fw]
        passed = sum(1 for r in g if r.get("bh_pass") == "True")
        out["families"].append({"week": fw, "tested": len(g), "bh_passed": passed,
                                "raw_pass_rate": sum(1 for r in g if float(r["raw_p"])<=0.05)/len(g)})
    return out

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("log"); l.add_argument("--thesis", required=True); l.add_argument("--p", required=True); l.add_argument("--family", default=None); l.add_argument("--decision", default="unknown")
    sub.add_parser("recompute"); sub.add_parser("status")
    a = p.parse_args()
    if a.cmd == "log": print(json.dumps(log(a.thesis, a.p, a.family, a.decision), indent=2))
    elif a.cmd == "recompute": print(json.dumps(recompute(), indent=2))
    elif a.cmd == "status": print(json.dumps(status(), indent=2))

if __name__ == "__main__": main()
