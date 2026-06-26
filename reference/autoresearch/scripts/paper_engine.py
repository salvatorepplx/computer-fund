"""Paper-trading engine for autoresearch theses.

Source of truth for armed paper positions. Daily MTM via finance tools.
Usage:
    python paper_engine.py open  --thesis <id> --ticker RDDT --side long --size 50000 --stop 0.92 --target 1.15
    python paper_engine.py mtm   --asof 2026-05-18
    python paper_engine.py kill_check
    python paper_engine.py portfolio_summary
"""
from __future__ import annotations
import argparse, csv, json, os, sys, subprocess
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
from _thesis_dirs import list_thesis_dirs
RUNS = ROOT / "runs"
RUNS.mkdir(exist_ok=True)
PORTFOLIO = RUNS / "PORTFOLIO.md"
CORPSES = RUNS / "CORPSES.md"

BOOK_COLS = ["date", "thesis_id", "pr_ref", "ticker", "side", "size_usd",
             "entry_px", "stop", "target", "status", "exit_date", "exit_px", "realized_pnl"]
MTM_COLS = ["date", "thesis_id", "ticker", "side", "size_usd",
            "entry_px", "mark_px", "unrealized_pnl_usd", "unrealized_pnl_pct"]

def _thesis_dir(thesis_id: str) -> Path:
    d = RUNS / thesis_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def _book_path(thesis_id: str) -> Path:
    return _thesis_dir(thesis_id) / "paper_book.csv"

def _mtm_path(thesis_id: str) -> Path:
    return _thesis_dir(thesis_id) / "paper_pnl.csv"

def _read_csv(path: Path) -> list[dict]:
    if not path.exists(): return []
    with path.open() as f: return list(csv.DictReader(f))

def _write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in cols})

def open_position(thesis_id, pr_ref, ticker, side, size_usd, entry_px, stop, target):
    bp = _book_path(thesis_id)
    rows = _read_csv(bp)
    rows.append({
        "date": date.today().isoformat(), "thesis_id": thesis_id, "pr_ref": pr_ref,
        "ticker": ticker, "side": side, "size_usd": size_usd, "entry_px": entry_px,
        "stop": stop, "target": target, "status": "OPEN",
        "exit_date": "", "exit_px": "", "realized_pnl": "",
    })
    _write_csv(bp, rows, BOOK_COLS)
    print(f"[OPEN] {thesis_id} {side} {ticker} ${size_usd} @ {entry_px} stop={stop} target={target}")

def _fetch_close(ticker: str, asof: str | None = None) -> float | None:
    """Use pplx finance tools if available, else fall back to yfinance via curl-free path."""
    # Try yfinance first (no network roundtrip via pplx, fastest)
    try:
        import yfinance as yf  # type: ignore
        t = yf.Ticker(ticker)
        h = t.history(period="5d")
        if not h.empty: return float(h["Close"].iloc[-1])
    except Exception:
        pass
    # Fallback: pplx finance CLI (price_history)
    try:
        out = subprocess.run(
            ["pplx-tool", "finance_price_history", "--ticker", ticker, "--lookback", "5d"],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(out.stdout)
        return float(data["prices"][-1]["close"])
    except Exception as e:
        print(f"[warn] price fetch failed for {ticker}: {e}", file=sys.stderr)
        return None

def mtm(asof: str | None = None):
    asof = asof or date.today().isoformat()
    all_mtm = []
    for tdir in list_thesis_dirs(RUNS):
        bp = tdir / "paper_book.csv"
        if not bp.exists(): continue
        rows = _read_csv(bp)
        mtm_rows = []
        for r in rows:
            if r.get("status") != "OPEN": continue
            mark = _fetch_close(r["ticker"], asof)
            if mark is None: continue
            entry = float(r["entry_px"]); size = float(r["size_usd"])
            mult = 1 if r["side"] == "long" else -1
            pnl_pct = mult * (mark - entry) / entry
            pnl_usd = pnl_pct * size
            mtm_rows.append({
                "date": asof, "thesis_id": r["thesis_id"], "ticker": r["ticker"],
                "side": r["side"], "size_usd": size, "entry_px": entry,
                "mark_px": mark, "unrealized_pnl_usd": round(pnl_usd, 2),
                "unrealized_pnl_pct": round(pnl_pct, 4),
            })
        if mtm_rows:
            existing = _read_csv(tdir / "paper_pnl.csv")
            _write_csv(tdir / "paper_pnl.csv", existing + mtm_rows, MTM_COLS)
            all_mtm.extend(mtm_rows)
    print(f"[MTM] marked {len(all_mtm)} positions as-of {asof}")
    return all_mtm

def kill_check():
    """Check kill switches: -15% drawdown, stop breach, target breach."""
    triggers = []
    for tdir in list_thesis_dirs(RUNS):
        bp = tdir / "paper_book.csv"; mp = tdir / "paper_pnl.csv"
        if not (bp.exists() and mp.exists()): continue
        book = _read_csv(bp); pnl = _read_csv(mp)
        for r in book:
            if r.get("status") != "OPEN": continue
            mark_rows = [p for p in pnl if p["thesis_id"] == r["thesis_id"] and p["ticker"] == r["ticker"]]
            if not mark_rows: continue
            latest = mark_rows[-1]
            pct = float(latest["unrealized_pnl_pct"])
            mark = float(latest["mark_px"]); entry = float(r["entry_px"])
            stop = float(r["stop"]) if r["stop"] else None
            target = float(r["target"]) if r["target"] else None
            reason = None
            if pct <= -0.15:
                reason = f"drawdown {pct:.1%} <= -15%"
            elif stop and ((r["side"]=="long" and mark <= stop*entry) or
                           (r["side"]=="short" and mark >= stop*entry)):
                reason = f"stop hit @ {mark}"
            elif target and ((r["side"]=="long" and mark >= target*entry) or
                             (r["side"]=="short" and mark <= target*entry)):
                reason = f"target hit @ {mark}"
            if reason:
                triggers.append({"thesis_id": r["thesis_id"], "ticker": r["ticker"], "reason": reason, "pnl_pct": pct})
                # mark closed
                r["status"] = "STOPPED" if "stop" in reason or "drawdown" in reason else "TARGET"
                r["exit_date"] = date.today().isoformat()
                r["exit_px"] = mark
                r["realized_pnl"] = round(float(latest["unrealized_pnl_usd"]), 2)
        _write_csv(bp, book, BOOK_COLS)
    print(f"[KILL] {len(triggers)} triggers"); print(json.dumps(triggers, indent=2))
    return triggers

def portfolio_summary():
    lines = ["# Paper-Trade Portfolio", f"_as-of {date.today().isoformat()}_\n", "| Thesis | Ticker | Side | Size | Entry | Mark | P&L % | P&L $ | Status |", "|---|---|---|---|---|---|---|---|---|"]
    total_pnl = 0.0; n_open = 0
    for tdir in list_thesis_dirs(RUNS):
        bp = tdir / "paper_book.csv"; mp = tdir / "paper_pnl.csv"
        if not bp.exists(): continue
        book = _read_csv(bp); pnl = _read_csv(mp) if mp.exists() else []
        for r in book:
            if r.get("status") != "OPEN": continue
            n_open += 1
            mark_rows = [p for p in pnl if p["thesis_id"] == r["thesis_id"] and p["ticker"] == r["ticker"]]
            mark = mark_rows[-1] if mark_rows else None
            pnl_pct = mark["unrealized_pnl_pct"] if mark else "—"
            pnl_usd = float(mark["unrealized_pnl_usd"]) if mark else 0
            total_pnl += pnl_usd
            lines.append(f"| {r['thesis_id']} | {r['ticker']} | {r['side']} | ${r['size_usd']} | {r['entry_px']} | {mark['mark_px'] if mark else '—'} | {pnl_pct} | {pnl_usd:.0f} | {r['status']} |")
    lines.append(f"\n**Open positions**: {n_open}  ·  **Total unrealized P&L**: ${total_pnl:.2f}")
    PORTFOLIO.write_text("\n".join(lines))
    print(PORTFOLIO.read_text())

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    op = sub.add_parser("open")
    for arg in ["thesis","pr_ref","ticker","side","size","entry","stop","target"]:
        op.add_argument(f"--{arg}", required=True)
    m = sub.add_parser("mtm"); m.add_argument("--asof", default=None)
    sub.add_parser("kill_check")
    sub.add_parser("portfolio_summary")
    a = p.parse_args()
    if a.cmd == "open":
        open_position(a.thesis, a.pr_ref, a.ticker, a.side, float(a.size),
                      float(a.entry), float(a.stop), float(a.target))
    elif a.cmd == "mtm": mtm(a.asof)
    elif a.cmd == "kill_check": kill_check()
    elif a.cmd == "portfolio_summary": portfolio_summary()

if __name__ == "__main__": main()
