"""Historical sweep — replay a hypothesis structure across many past events.

Inputs: event calendar (data/events/*.csv) + cached prices (data/cache/prices/).
Output: per-event abnormal returns, aggregate statistics, BH-corrected p-values.

Usage:
    python historical_sweep.py --event_calendar data/events/fomc_history.csv \
        --tickers SPY,TLT,GLD --window_pre 1 --window_post 5 --out runs/SWEEPS/fomc_xtest
"""
from __future__ import annotations
import argparse, csv, json
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "prices"

def _price_path(t): return CACHE / f"{t.replace('^','_').replace('/','_').replace('-','_')}.csv"

def _load_prices(t):
    import pandas as pd
    p = _price_path(t)
    if not p.exists(): return None
    df = pd.read_csv(p, index_col=0, parse_dates=True)
    if "Close" in df.columns: return df["Close"]
    # fallback to first numeric column
    return df.select_dtypes("number").iloc[:, 0]

def _load_events(path):
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            try: out.append({"date": date.fromisoformat(r["date"]), "event": r.get("event",""), "notes": r.get("notes","")})
            except ValueError: continue
    return sorted(out, key=lambda x: x["date"])

def sweep(event_calendar, tickers, window_pre=1, window_post=5, out_dir=None):
    import pandas as pd, numpy as np
    events = _load_events(event_calendar)
    if not events: return {"ok": False, "error": "no events parsed"}

    # Pre-load all ticker price series
    series = {}
    for t in tickers:
        s = _load_prices(t)
        if s is not None: series[t] = s
    if not series: return {"ok": False, "error": "no cached prices for any ticker", "needed": tickers}

    results = []
    for ev in events:
        ev_dt = pd.Timestamp(ev["date"])
        per_ticker = {}
        for t, s in series.items():
            # find the event-anchor index
            try:
                # Use index loc — find nearest trading day at/before ev_dt
                anchor_idx = s.index.searchsorted(ev_dt)
                if anchor_idx >= len(s) or anchor_idx < window_pre: continue
                pre_px = float(s.iloc[anchor_idx - window_pre])
                post_idx = min(anchor_idx + window_post, len(s) - 1)
                post_px = float(s.iloc[post_idx])
                ret = (post_px - pre_px) / pre_px
                per_ticker[t] = round(ret, 5)
            except Exception:
                continue
        if per_ticker:
            results.append({"date": ev["date"].isoformat(), "event": ev["event"], "returns": per_ticker})

    # Aggregate per ticker
    aggregate = {}
    for t in series:
        vals = [r["returns"][t] for r in results if t in r["returns"]]
        if len(vals) < 5: continue
        arr = np.array(vals)
        mean = float(arr.mean()); std = float(arr.std()); n = len(arr)
        tstat = (mean / (std / (n ** 0.5))) if std > 0 else 0
        # rough two-sided p-value approximation via normal cdf
        from math import erf, sqrt
        p_val = 2 * (1 - 0.5 * (1 + erf(abs(tstat) / sqrt(2))))
        aggregate[t] = {"n": n, "mean": round(mean, 5), "std": round(std, 5),
                        "t_stat": round(tstat, 3), "p_uncorrected": round(p_val, 5),
                        "hit_rate": round(float((arr > 0).mean()), 3)}

    # BH correction across tickers
    sorted_ps = sorted([(t, m["p_uncorrected"]) for t, m in aggregate.items()], key=lambda x: x[1])
    m_tests = len(sorted_ps)
    for i, (t, p) in enumerate(sorted_ps, start=1):
        q = p * m_tests / i
        aggregate[t]["bh_q"] = round(min(q, 1.0), 5)
        aggregate[t]["bh_pass"] = bool(q <= 0.05)

    out = {
        "ok": True,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "event_calendar": str(event_calendar),
        "tickers": tickers,
        "window": [window_pre, window_post],
        "n_events": len(results),
        "per_event_first10": results[:10],
        "aggregate": aggregate,
        "summary": {"survivors_bh": [t for t, m in aggregate.items() if m.get("bh_pass")]},
    }
    if out_dir:
        out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "sweep_results.json").write_text(json.dumps(out, indent=2, default=str))
    return out

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--event_calendar", required=True)
    p.add_argument("--tickers", required=True, help="comma-separated")
    p.add_argument("--window_pre", type=int, default=1)
    p.add_argument("--window_post", type=int, default=5)
    p.add_argument("--out", default=None)
    a = p.parse_args()
    tickers = a.tickers.split(",")
    print(json.dumps(sweep(a.event_calendar, tickers, a.window_pre, a.window_post, a.out), indent=2, default=str))

if __name__ == "__main__": main()
