"""Single source of truth for 'what counts as a thesis directory under runs/'.

Importable by orchestrator, paper_engine, run_evals, meta_orchestrator, frontier,
and any future script. Prevents the SWEEPS/CRITIQUES/etc folders from being
mistaken for theses.
"""
from __future__ import annotations
from pathlib import Path

# Explicit deny-list. Add new infra/output folders here when they appear.
NON_THESIS_DIRS = {
    "__pycache__", "SWEEPS", "CRITIQUES", "USER_SEEDS",
    ".portfolio_snapshots", "deep_mining", "HARNESS-PRS",
}

def is_thesis_dir(tdir: Path) -> bool:
    """A directory is a thesis only if (a) name not in deny-list, (b) not hidden,
    (c) has a STATUS file. Infra/output folders fail (c)."""
    if tdir.name in NON_THESIS_DIRS: return False
    if tdir.name.startswith("."): return False
    if not tdir.is_dir(): return False
    return (tdir / "STATUS").exists()

def list_thesis_dirs(runs_root: Path):
    """Yield Path objects for every valid thesis dir under runs_root."""
    if not runs_root.exists(): return
    for tdir in sorted(p for p in runs_root.iterdir() if p.is_dir()):
        if is_thesis_dir(tdir): yield tdir
