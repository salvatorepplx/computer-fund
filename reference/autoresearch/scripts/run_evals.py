"""Deterministic eval suite. Runs all E-CAP-* and E-REG-* evals over runs/.

Usage:
    python run_evals.py                   # run all, print summary
    python run_evals.py --eval E-CAP-01   # run one
    python run_evals.py --week 2026-W21   # write weekly snapshot
"""
from __future__ import annotations
import argparse, csv, json, os, re, subprocess, sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
EVALS = ROOT / "evals"
SCORES = EVALS / "scores"
SCORES.mkdir(parents=True, exist_ok=True)
REGISTRY = json.loads((EVALS / "registry.json").read_text())

from _thesis_dirs import list_thesis_dirs

def _theses():
    yield from list_thesis_dirs(RUNS)

def _status(tdir): return (tdir / "STATUS").read_text().strip()

def _is_template_stub(pr_text: str) -> bool:
    """A PR is a template stub if it still contains scaffolder placeholders.
    Watchlist insight from meta-orchestrator HPR-001 reasoning pass (2026-05-18).
    Stubs should be excluded from CAP/REG denominators so they don't trigger
    false-positive bottleneck flags."""
    markers = [
        "DRAFT | ARMED | MERGED | ITERATING | KILLED",
        "On <asset>, signal <S> predicts",
        "<one-line title>",
    ]
    return any(m in pr_text for m in markers)

def _read_prs(tdir, include_stubs=False):
    prs = sorted((tdir / "prs").glob("PR-*.md")) if (tdir / "prs").exists() else []
    out = []
    for p in prs:
        txt = p.read_text()
        if (not include_stubs) and _is_template_stub(txt): continue
        out.append((p, txt))
    return out

def _read_paper(tdir):
    bp = tdir / "paper_book.csv"
    if not bp.exists(): return []
    with bp.open() as f: return list(csv.DictReader(f))

def _read_pnl(tdir):
    mp = tdir / "paper_pnl.csv"
    if not mp.exists(): return []
    with mp.open() as f: return list(csv.DictReader(f))

# ---------- CAPABILITY EVALS ----------

def e_cap_01():
    """Reviewer score → realized P&L correlation."""
    pairs = []
    for tdir in _theses():
        prs = _read_prs(tdir)
        for pr_path, txt in prs:
            m = re.search(r"Score \(0-?10\).*?\*\*\s*([\d.]+)\s*/\s*10\s*\*\*", txt)
            if not m: continue
            score = float(m.group(1))
            # find matching closed paper trade in book
            book = _read_paper(tdir)
            for row in book:
                if row.get("pr_ref") == pr_path.stem and row.get("status") in ("STOPPED","TARGET","CLOSED"):
                    pnl = float(row.get("realized_pnl", 0) or 0)
                    size = float(row.get("size_usd", 1) or 1)
                    pairs.append((score, pnl/size))
    if len(pairs) < 3:
        return {"score": None, "n": len(pairs), "note": "insufficient data"}
    # spearman
    import statistics
    n = len(pairs)
    rx = _rank([p[0] for p in pairs]); ry = _rank([p[1] for p in pairs])
    mx = statistics.mean(rx); my = statistics.mean(ry)
    num = sum((rx[i]-mx)*(ry[i]-my) for i in range(n))
    den = (sum((rx[i]-mx)**2 for i in range(n)) * sum((ry[i]-my)**2 for i in range(n)))**0.5
    rho = num/den if den else 0
    return {"score": rho, "n": n, "target": 0.5, "passing": rho >= 0.5}

def _rank(xs):
    s = sorted((v,i) for i,v in enumerate(xs))
    r = [0]*len(xs)
    for rank,(v,i) in enumerate(s): r[i] = rank
    return r

def e_cap_02():
    """Falsifier hit rate on theses that lost money post-MERGE."""
    bad_merged = 0; bad_caught = 0
    for tdir in _theses():
        if _status(tdir) != "MERGED": continue
        pnl = _read_pnl(tdir)
        if not pnl: continue
        last = pnl[-1]
        pct = float(last.get("unrealized_pnl_pct", 0))
        if pct < -0.10:  # lost > 10%
            bad_merged += 1
            # any subsequent KILL PR with a falsifier flag?
            for _, txt in _read_prs(tdir):
                if "KILL" in txt and "falsifier" in txt.lower(): bad_caught += 1; break
    rate = bad_caught / bad_merged if bad_merged else None
    return {"score": rate, "n": bad_merged, "target": 0.80,
            "passing": (rate is None) or rate >= 0.80}

def e_cap_03():
    """Seeder edge: % of iterated SEEDED theses that survived to ARMED+.
    Excludes theses whose only PR is a template stub (not yet iterated)."""
    total = 0; armed = 0; pending = 0
    for tdir in _theses():
        iterated = bool(_read_prs(tdir, include_stubs=False)) or _status(tdir) != "SEEDED"
        if not iterated: pending += 1; continue
        total += 1
        if _status(tdir) in ("ARMED","MERGED"): armed += 1
    pct = armed / total if total else None
    return {"score": pct, "n_iterated": total, "n_pending_iteration": pending,
            "target": 0.35,
            "passing": (pct is None) or pct >= 0.35,
            "note": f"{pending} thesis/theses awaiting first iteration" if pending else None}

def e_cap_04():
    """Avg iteration count at MERGE."""
    depths = []
    for tdir in _theses():
        if _status(tdir) == "MERGED":
            depths.append(len(list((tdir / "prs").glob("PR-*.md"))))
    if not depths: return {"score": None, "n": 0}
    avg = sum(depths)/len(depths)
    return {"score": avg, "n": len(depths), "target_max": 3.0, "passing": avg <= 3.0}

def e_cap_05():
    """Avg iterations before KILL (we want fast kills)."""
    depths = []
    for tdir in _theses():
        if _status(tdir) == "KILLED":
            depths.append(len(list((tdir / "prs").glob("PR-*.md"))))
    if not depths: return {"score": None, "n": 0}
    avg = sum(depths)/len(depths)
    return {"score": avg, "n": len(depths), "target_max": 2.0, "passing": avg <= 2.0}

def e_cap_06():
    """Armed portfolio annualized Sharpe (rough — needs ≥20 trading days)."""
    daily = {}
    for tdir in _theses():
        for row in _read_pnl(tdir):
            daily.setdefault(row["date"], 0.0)
            daily[row["date"]] += float(row.get("unrealized_pnl_usd", 0) or 0)
    if len(daily) < 20: return {"score": None, "n": len(daily), "note": "need 20+ days"}
    vals = list(daily.values())
    rets = [vals[i] - vals[i-1] for i in range(1, len(vals))]
    import statistics
    mean = statistics.mean(rets); sd = statistics.stdev(rets) if len(rets) > 1 else 0
    sharpe = (mean / sd) * (252**0.5) if sd else 0
    return {"score": sharpe, "n": len(daily), "target": 1.0, "passing": sharpe >= 1.0}

# ---------- REGRESSION EVALS ----------

def e_reg_01():
    """Look-ahead leak audit on merged theses — every MERGE PR must mention 'look-ahead'."""
    fails = []
    for tdir in _theses():
        if _status(tdir) != "MERGED": continue
        ok = False
        for _, txt in _read_prs(tdir):
            if re.search(r"look[- ]ahead", txt, re.I): ok = True; break
        if not ok: fails.append(tdir.name)
    return {"score": 1 - len(fails)/max(1, sum(1 for t in _theses() if _status(t)=="MERGED")),
            "fails": fails, "threshold": 1.0, "passing": not fails}

def e_reg_02():
    """All falsifiers run per PR."""
    fails = []
    required = ["random-label", "earnings", "date split", "cost", "placebo"]
    for tdir in _theses():
        for pr_path, txt in _read_prs(tdir):
            tl = txt.lower()
            missing = [k for k in required if k.split()[0] not in tl]
            if missing: fails.append({"pr": str(pr_path), "missing": missing})
    return {"fails_count": len(fails), "fails_sample": fails[:5],
            "threshold": 1.0, "passing": not fails}

def e_reg_03():
    """Pre-registered targets present per PR."""
    fails = []
    for tdir in _theses():
        for pr_path, txt in _read_prs(tdir):
            if not re.search(r"Pre-?reg(istration|istered)", txt, re.I):
                fails.append(str(pr_path))
    return {"fails_count": len(fails), "fails_sample": fails[:5],
            "threshold": 1.0, "passing": not fails}

def e_reg_04():
    """Every MERGED thesis has ≥20 paper-trade days."""
    fails = []
    for tdir in _theses():
        if _status(tdir) != "MERGED": continue
        pnl = _read_pnl(tdir)
        days = len(set(r["date"] for r in pnl))
        if days < 20: fails.append({"id": tdir.name, "days": days})
    return {"fails_count": len(fails), "fails": fails,
            "threshold": 1.0, "passing": not fails}

def e_reg_05():
    """Every KILLED thesis has a CORPSES.md entry."""
    corpses = (RUNS / "CORPSES.md").read_text() if (RUNS / "CORPSES.md").exists() else ""
    fails = [tdir.name for tdir in _theses()
             if _status(tdir) == "KILLED" and tdir.name not in corpses]
    return {"fails_count": len(fails), "fails": fails,
            "threshold": 1.0, "passing": not fails}

def e_reg_06():
    """Skill validates."""
    res = subprocess.run(["agentskills","validate",str(ROOT)], capture_output=True, text=True)
    ok = "Valid skill" in res.stdout
    return {"passing": ok, "stdout": res.stdout.strip()[:200]}

EVAL_FNS = {
    "E-CAP-01": e_cap_01, "E-CAP-02": e_cap_02, "E-CAP-03": e_cap_03,
    "E-CAP-04": e_cap_04, "E-CAP-05": e_cap_05, "E-CAP-06": e_cap_06,
    "E-REG-01": e_reg_01, "E-REG-02": e_reg_02, "E-REG-03": e_reg_03,
    "E-REG-04": e_reg_04, "E-REG-05": e_reg_05, "E-REG-06": e_reg_06,
}

def run_all(week_tag=None):
    results = {}
    for eid, fn in EVAL_FNS.items():
        try: results[eid] = fn()
        except Exception as e: results[eid] = {"error": str(e)}
    week_tag = week_tag or date.today().strftime("%Y-W%V")
    out = SCORES / f"{week_tag}.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    # human-readable summary
    summary = [f"# Eval Run · {week_tag}\n"]
    for eid, r in results.items():
        meta = REGISTRY["evals"][eid]
        passing = r.get("passing")
        mark = "✅" if passing else ("❌" if passing is False else "—")
        summary.append(f"- {mark} **{eid}** · {meta['name']} · {json.dumps({k:v for k,v in r.items() if k!='fails_sample'})}")
    (SCORES / f"{week_tag}.md").write_text("\n".join(summary))
    print("\n".join(summary))
    return results

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--eval", default=None)
    p.add_argument("--week", default=None)
    a = p.parse_args()
    if a.eval:
        print(json.dumps(EVAL_FNS[a.eval](), indent=2, default=str))
    else:
        run_all(a.week)

if __name__ == "__main__": main()
