"""Explorer: one bandit-pull per invocation = one new hypothesis to test.

Decoupled from catalysts. Every call samples a hypothesis tuple from the
hypothesis-space grammar, writes a thesis.md, and queues it for the iteration loop.

Usage:
    python explorer.py explore                # draw one new hypothesis, scaffold thesis dir
    python explorer.py explore --n 10         # draw 10 in batch
    python explorer.py frontier               # show current surviving (signal,universe,horizon,structure) tuples
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
EVALS = ROOT / "evals"
FRONTIER = EVALS / "frontier.json"

def _slug(h):
    return f"h_{h['signal']}_{h['universe']}_{h['horizon']}_{h['structure']}".lower().replace("|","_")

def scaffold(h):
    tdir = RUNS / _slug(h)
    if tdir.exists():
        # name collision — append timestamp
        tdir = RUNS / f"{_slug(h)}_{datetime.utcnow().strftime('%H%M%S')}"
    tdir.mkdir(parents=True)
    (tdir / "STATUS").write_text("SEEDED")
    thesis_md = f"""# Generated Thesis · {h['thesis_id']}

**Generated**: {h['sampled_at']}
**Generator**: explorer.py (Thompson sampling over hypothesis-space grammar)

## Tuple
- **signal**: `{h['signal']}`
- **universe**: `{h['universe']}`
- **horizon**: `{h['horizon']}`
- **structure**: `{h['structure']}`

## Hypothesis (to be filled by the iteration agent)
On the {h['universe']} universe, the {h['signal']} signal predicts {h['horizon']} returns
with a tradeable edge when expressed as a {h['structure']} structure.

The iteration agent must:
1. Read `references/hypothesis-space.md` for signal/universe definitions
2. Pull the relevant data for `{h['signal']}` from `data/registry.json`
3. Form the cross-sectional or single-name signal series with proper lag (≥1d)
4. Backtest the `{h['structure']}` over the `{h['horizon']}` horizon
5. Run the full falsifier suite from `references/falsification-playbook.md`
6. Compute random-label placebo p-value
7. Log via `python scripts/multiple_testing.py log --thesis {h['thesis_id']} --p <p>`
8. Update bandit arms via `python scripts/hypothesis_space.py update --axis ... --value ... --outcome ...`
9. If signal survives single-name, run cross-sectional generalization across the full universe
10. Write the PR per `references/pr-format.md`

## Why this hypothesis was sampled
The bandit drew this from the current posterior. Check `evals/bandit_arms.json` for
the posterior means at sampling time.
"""
    (tdir / "thesis.md").write_text(thesis_md)
    return tdir

def explore(n=1):
    # call hypothesis_space.py to draw
    res = subprocess.run([sys.executable, str(ROOT/"scripts"/"hypothesis_space.py"),
                          "sample", "--n", str(n)], capture_output=True, text=True)
    if res.returncode != 0:
        return {"error": res.stderr}
    samples = json.loads(res.stdout)
    out = []
    for h in samples:
        td = scaffold(h)
        # also scaffold PR-001 stub
        subprocess.run([sys.executable, str(ROOT/"scripts"/"run_iteration.py"),
                        "--thesis", td.name,
                        "--title", f"{h['signal']} on {h['universe']} {h['horizon']} {h['structure']}"],
                       capture_output=True, text=True)
        out.append({"thesis_id": h["thesis_id"], "dir": str(td)})
    return out

def frontier():
    if not FRONTIER.exists(): return {"surviving": [], "note": "frontier not yet built"}
    return json.loads(FRONTIER.read_text())

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("explore"); e.add_argument("--n", type=int, default=1)
    sub.add_parser("frontier")
    a = p.parse_args()
    if a.cmd == "explore": print(json.dumps(explore(a.n), indent=2))
    elif a.cmd == "frontier": print(json.dumps(frontier(), indent=2))

if __name__ == "__main__": main()
