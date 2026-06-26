"""Deterministic data fetcher with a persistent cache.

All historical data the system needs is fetched and cached under data/cache/.
Re-running the same fetch is idempotent (cache hit) — so cron-fired sweeps
become reproducible and cheap.

Currently supported sources:
- yfinance for OHLCV (any ticker)
- FRED for macro series (DGS10, DGS2, T10YIE, NFCI, USEPUINDXD, BAMLH0A0HYM2, etc)
- yfinance for earnings dates per ticker

Usage:
    python data_fetcher.py prices --ticker SPY --years 5
    python data_fetcher.py prices --tickers SPY,QQQ,IWM --years 5
    python data_fetcher.py fred --series DGS10 --years 5
    python data_fetcher.py earnings --ticker NVDA --years 5
    python data_fetcher.py cache_status
    python data_fetcher.py warm                       # fetch the standard pack
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
PRICES = CACHE / "prices"; PRICES.mkdir(exist_ok=True)
FRED = CACHE / "fred"; FRED.mkdir(exist_ok=True)
EARNINGS = CACHE / "earnings"; EARNINGS.mkdir(exist_ok=True)
EVENTS = ROOT / "data" / "events"; EVENTS.mkdir(exist_ok=True)

# Standard warm pack: universes worth pre-fetching
WARM_TICKERS = sorted(set([
    "SPY","QQQ","IWM","DIA","TLT","IEF","SHY","TIP","HYG","LQD","GLD","SLV","USO","UNG","DBC","UUP","^VIX","^VIX3M","^SKEW",
    "XLK","XLF","XLE","XLU","XLV","XLY","XLI","XLB","XLP","XLRE","XLC",
    "MTUM","QUAL","VLUE","USMV","SPLV","SIZE","COWZ",
    # Tech megacaps
    "NVDA","AVGO","AMD","ORCL","TSM","INTC","MU","SNDK","WDC","MSFT","GOOGL","META","AAPL","AMZN","NFLX","ADBE","CRM",
    # Social / retail attention
    "RDDT","SNAP","PINS","RBLX","COIN","HOOD","PLTR","CVNA","TSLA","GME","AMC","HIMS","SOFI","RIVN","LCID",
    # AI / power
    "BE","NRG","VST","CEG","GEV","ETR","CRWV","LUMN","COHR","CORZ","RIOT","IREN","CIFR","APLD",
    # Banks / commodities
    "JPM","BAC","WFC","C","GS","XOM","CVX","COP","FCX","SCCO","NEM",
    "BTC-USD","ETH-USD","SOL-USD",
    "SMH","SOXX",
]))

WARM_FRED = ["DGS10","DGS2","DGS3MO","T10YIE","NFCI","USEPUINDXD","BAMLH0A0HYM2","BAMLC0A0CM","UNRATE","CPIAUCSL"]

def _price_path(ticker): return PRICES / f"{ticker.replace('^','_').replace('/','_').replace('-','_')}.csv"
def _fred_path(series): return FRED / f"{series}.csv"
def _earn_path(ticker): return EARNINGS / f"{ticker.replace('^','_')}_earnings.csv"

def _fresh(p: Path, max_age_hours=24):
    if not p.exists(): return False
    age = (datetime.now().timestamp() - p.stat().st_mtime) / 3600
    return age < max_age_hours

def fetch_prices(tickers, years=5, force=False):
    import yfinance as yf
    if isinstance(tickers, str): tickers = [tickers]
    end = date.today(); start = end - timedelta(days=365*years)
    out = {}
    for t in tickers:
        p = _price_path(t)
        if _fresh(p) and not force: out[t] = {"path": str(p), "cache": "hit", "rows": _row_count(p)}; continue
        try:
            df = yf.download(t, start=str(start), end=str(end), progress=False, auto_adjust=True)
            if df.empty:
                out[t] = {"path": str(p), "cache": "miss", "rows": 0, "error": "empty"}
                continue
            # Flatten multi-index columns if present
            if hasattr(df.columns, "levels"): df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df.to_csv(p)
            out[t] = {"path": str(p), "cache": "fresh", "rows": len(df)}
        except Exception as e:
            out[t] = {"path": str(p), "cache": "miss", "error": str(e)}
    return out

def _row_count(p):
    try:
        with p.open() as f: return sum(1 for _ in f) - 1
    except Exception: return 0

def fetch_fred(series_list, years=10, force=False):
    """FRED via pandas_datareader if available, else direct CSV from fred.stlouisfed.org."""
    if isinstance(series_list, str): series_list = [series_list]
    out = {}
    end = date.today(); start = end - timedelta(days=365*years)
    try:
        import pandas_datareader.data as pdr
        for s in series_list:
            p = _fred_path(s)
            if _fresh(p) and not force: out[s] = {"path": str(p), "cache": "hit", "rows": _row_count(p)}; continue
            try:
                df = pdr.DataReader(s, "fred", start, end)
                df.to_csv(p)
                out[s] = {"path": str(p), "cache": "fresh", "rows": len(df)}
            except Exception as e:
                out[s] = {"path": str(p), "cache": "miss", "error": str(e)}
    except ImportError:
        # fallback to direct CSV download
        import urllib.request
        for s in series_list:
            p = _fred_path(s)
            if _fresh(p) and not force: out[s] = {"path": str(p), "cache": "hit", "rows": _row_count(p)}; continue
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}&cosd={start}&coed={end}"
            try:
                urllib.request.urlretrieve(url, p)
                out[s] = {"path": str(p), "cache": "fresh", "rows": _row_count(p)}
            except Exception as e:
                out[s] = {"path": str(p), "cache": "miss", "error": str(e)}
    return out

def fetch_earnings(tickers, force=False):
    import yfinance as yf
    if isinstance(tickers, str): tickers = [tickers]
    out = {}
    for t in tickers:
        p = _earn_path(t)
        if _fresh(p, max_age_hours=24*7) and not force: out[t] = {"path": str(p), "cache": "hit", "rows": _row_count(p)}; continue
        try:
            tk = yf.Ticker(t)
            df = tk.get_earnings_dates(limit=60) if hasattr(tk, "get_earnings_dates") else None
            if df is None or df.empty:
                out[t] = {"path": str(p), "cache": "miss", "rows": 0, "error": "no earnings data"}
                continue
            df.to_csv(p)
            out[t] = {"path": str(p), "cache": "fresh", "rows": len(df)}
        except Exception as e:
            out[t] = {"path": str(p), "cache": "miss", "error": str(e)}
    return out

def cache_status():
    return {
        "prices_cached": len(list(PRICES.glob("*.csv"))),
        "fred_cached": len(list(FRED.glob("*.csv"))),
        "earnings_cached": len(list(EARNINGS.glob("*.csv"))),
        "events_files": [p.name for p in EVENTS.glob("*.csv")],
        "total_size_mb": round(sum(p.stat().st_size for p in CACHE.rglob("*.csv")) / 1e6, 2),
    }

def warm(force=False):
    """Fetch the standard pack so the sweep cron has data to work with."""
    res = {"prices": fetch_prices(WARM_TICKERS, years=5, force=force),
           "fred": fetch_fred(WARM_FRED, years=10, force=force),
           "earnings": fetch_earnings(WARM_TICKERS[:30], force=force)}  # limit earnings calls
    res["status"] = cache_status()
    return res

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prices"); pr.add_argument("--ticker", default=None); pr.add_argument("--tickers", default=None); pr.add_argument("--years", type=int, default=5); pr.add_argument("--force", action="store_true")
    fr = sub.add_parser("fred"); fr.add_argument("--series", required=True); fr.add_argument("--years", type=int, default=10); fr.add_argument("--force", action="store_true")
    er = sub.add_parser("earnings"); er.add_argument("--ticker", required=True); er.add_argument("--force", action="store_true")
    sub.add_parser("cache_status")
    wm = sub.add_parser("warm"); wm.add_argument("--force", action="store_true")
    a = p.parse_args()
    if a.cmd == "prices":
        tickers = [a.ticker] if a.ticker else a.tickers.split(",")
        print(json.dumps(fetch_prices(tickers, a.years, a.force), indent=2))
    elif a.cmd == "fred":
        print(json.dumps(fetch_fred(a.series.split(","), a.years, a.force), indent=2))
    elif a.cmd == "earnings":
        print(json.dumps(fetch_earnings([a.ticker], a.force), indent=2))
    elif a.cmd == "cache_status":
        print(json.dumps(cache_status(), indent=2))
    elif a.cmd == "warm":
        print(json.dumps(warm(a.force), indent=2, default=str))

if __name__ == "__main__": main()
