"""Holdout vault manager.

Reserves a random 30% slice of (universe × time) that exploration NEVER touches.
On MERGE attempt, the thesis is replayed against the held-out slice exactly once.
Failure on the holdout = permanent MERGE block for that (signal, universe, horizon).

The vault is fixed for the calendar year; redrawn each January 1.

Usage:
    python holdout_vault.py init --year 2026
    python holdout_vault.py is_holdout --ticker RDDT --date 2025-11-14
    python holdout_vault.py validate --thesis attention_fade_rddt
"""
from __future__ import annotations
import argparse, csv, json, random
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
VAULT_DIR = EVALS / "holdout"
VAULT_DIR.mkdir(parents=True, exist_ok=True)

def vault_path(year): return VAULT_DIR / f"vault_{year}.json"

def init(year, seed=42):
    """Create a holdout map: each (ticker, date) → bool. 30% True, fixed per year."""
    # We don't enumerate tickers up front; we record only the random seed and date bands
    # since the actual check is done by hash(ticker+date) % 100 < 30 — fully deterministic.
    v = {"year": year, "seed": seed, "method": "deterministic_hash",
         "fdr": 0.30, "created_at": datetime.now(timezone.utc).isoformat()}
    vault_path(year).write_text(json.dumps(v, indent=2))
    return v

def _hash_key(ticker, d):
    import hashlib
    return int(hashlib.md5(f"{ticker}|{d}".encode()).hexdigest(), 16) % 1000

def is_holdout(ticker, d, year=None):
    year = year or datetime.now(timezone.utc).year
    vp = vault_path(year)
    if not vp.exists(): init(year)
    v = json.loads(vp.read_text())
    seed = v["seed"]
    threshold = int(v["fdr"] * 1000)
    h = _hash_key(f"{ticker}_{seed}", d)
    return h < threshold

def validate(thesis_id, signal_days_csv=None):
    """Stub for the validation step. The actual replay logic must:
      1. Read the thesis's signal-day list
      2. Filter to days that are in the vault (~30% expected)
      3. Re-run the backtest on those days only
      4. Return Sharpe + p-value on the held-out subset
    Returns a stub result that the parent agent must populate.
    """
    return {"thesis": thesis_id, "status": "VALIDATION_STUB",
            "note": "Parent agent must run the replay; this script provides the holdout mask"}

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init"); i.add_argument("--year", type=int, required=True)
    q = sub.add_parser("is_holdout"); q.add_argument("--ticker", required=True); q.add_argument("--date", required=True)
    v = sub.add_parser("validate"); v.add_argument("--thesis", required=True)
    a = p.parse_args()
    if a.cmd == "init": print(json.dumps(init(a.year), indent=2))
    elif a.cmd == "is_holdout": print(json.dumps({"is_holdout": is_holdout(a.ticker, a.date)}, indent=2))
    elif a.cmd == "validate": print(json.dumps(validate(a.thesis), indent=2))

if __name__ == "__main__": main()
