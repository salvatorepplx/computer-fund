"""Single-iteration runner. Given a thesis_id, runs Steps 1-5 of the SKILL.md protocol.

Note: this orchestrates the human/agent workflow — heavy lifting (tree-search backtest,
reviewer subagent, paper-trade arming) is invoked by the parent agent. This script
provides the scaffolding (file layout, next-PR numbering, status updates).
"""
from __future__ import annotations
import argparse, os
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"

def next_pr_num(thesis_dir: Path) -> int:
    prs = thesis_dir / "prs"; prs.mkdir(exist_ok=True)
    nums = [int(p.stem.split("-")[1]) for p in prs.glob("PR-*.md") if p.stem.split("-")[1].isdigit()]
    return (max(nums) + 1) if nums else 1

def scaffold_pr(thesis_id: str, title: str, parent: str | None = None) -> Path:
    tdir = RUNS / thesis_id; tdir.mkdir(parents=True, exist_ok=True)
    n = next_pr_num(tdir)
    pr_path = tdir / "prs" / f"PR-{n:03d}.md"
    parent_str = parent or ("PR-{:03d}".format(n-1) if n > 1 else "(root)")
    template = (ROOT / "references" / "pr-format.md").read_text()
    # extract the template block
    start = template.find("```markdown") + len("```markdown\n")
    end = template.find("```", start)
    body = template[start:end].replace("PR-NNN", f"PR-{n:03d}").replace("NNN", f"{n:03d}")
    body = body.replace("YYYY-MM-DD", date.today().isoformat())
    body = body.replace("<slug>", thesis_id)
    body = body.replace("PR-(NNN-1) | (root)", parent_str)
    body = body.replace("<one-line title>", title)
    pr_path.write_text(body)
    return pr_path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--thesis", required=True, help="thesis slug")
    p.add_argument("--title", required=True, help="one-line PR title")
    p.add_argument("--parent", default=None)
    a = p.parse_args()
    pr_path = scaffold_pr(a.thesis, a.title, a.parent)
    print(f"[SCAFFOLD] {pr_path}")

if __name__ == "__main__": main()
