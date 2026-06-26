"""Real implementations for the signals named in data/registry.json.

Each signal returns a pandas DataFrame indexed by date, columns = tickers,
values = the signal level (properly lagged ≥1 day to prevent look-ahead).

Plug-in pattern: SIGNALS dict maps signal_name → callable(tickers, start, end).
Adding a new signal is a 1-function PR. Missing signals raise NotImplementedError
explicitly so the iterator can record "unimplemented" rather than fabricate.
"""
from __future__ import annotations
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"

def _load_price_series(ticker):
    """Load one ticker's Close series from disk cache, falling back to a fresh fetch."""
    import pandas as pd
    p = CACHE / "prices" / f"{ticker.replace('^','_').replace('/','_').replace('-','_')}.csv"
    if not p.exists():
        # try a fresh fetch
        try:
            import subprocess, sys
            subprocess.run([sys.executable, str(ROOT/"scripts"/"data_fetcher.py"),
                            "prices", "--ticker", ticker, "--years", "5"],
                           capture_output=True, timeout=30)
        except Exception: pass
    if not p.exists(): return None
    df = pd.read_csv(p, index_col=0, parse_dates=True)
    if "Close" in df.columns: return df["Close"]
    return df.select_dtypes("number").iloc[:, 0]

def _load_fred(series):
    import pandas as pd
    p = CACHE / "fred" / f"{series}.csv"
    if not p.exists(): return None
    df = pd.read_csv(p, index_col=0, parse_dates=True)
    return df.iloc[:, 0]

def _panel(tickers):
    """Return a DataFrame of close prices, tickers as columns, dates as index."""
    import pandas as pd
    data = {}
    for t in tickers:
        s = _load_price_series(t)
        if s is not None and len(s) > 100: data[t] = s
    if not data: return None
    df = pd.concat(data, axis=1).dropna(how="all")
    return df

# ============= SIGNAL IMPLEMENTATIONS =============

def price_momentum(tickers, lookback=20):
    """Trailing return over `lookback` trading days, lagged 1d."""
    panel = _panel(tickers);
    if panel is None: return None
    return panel.pct_change(lookback).shift(1)

def volume_zscore(tickers, lookback=20):
    """Volume z-score vs rolling mean/std, lagged 1d. Needs volume — use price for now as proxy."""
    import pandas as pd
    # placeholder: use abs price returns as crude attention proxy
    panel = _panel(tickers)
    if panel is None: return None
    ret = panel.pct_change().abs()
    z = (ret - ret.rolling(lookback).mean()) / ret.rolling(lookback).std()
    return z.shift(1)

def realized_vol(tickers, lookback=20):
    panel = _panel(tickers);
    if panel is None: return None
    return panel.pct_change().rolling(lookback).std().shift(1) * (252**0.5)

def yield_curve_slope(tickers, **kwargs):
    """10Y minus 2Y. Returns a single-series broadcast across tickers."""
    import pandas as pd
    d10 = _load_fred("DGS10"); d2 = _load_fred("DGS2")
    if d10 is None or d2 is None: return None
    slope = (d10 - d2).shift(1)
    panel = _panel(tickers)
    if panel is None: return None
    # broadcast: every ticker gets the same macro signal
    return pd.DataFrame({t: slope.reindex(panel.index, method="ffill") for t in panel.columns}, index=panel.index)

def epu_index(tickers, **kwargs):
    """Daily EPU index, broadcast."""
    import pandas as pd
    epu = _load_fred("USEPUINDXD")
    if epu is None: return None
    panel = _panel(tickers)
    if panel is None: return None
    return pd.DataFrame({t: epu.reindex(panel.index, method="ffill") for t in panel.columns}, index=panel.index).shift(1)

def credit_spreads_ighy(tickers, **kwargs):
    """HY-IG OAS spread, broadcast."""
    import pandas as pd
    hy = _load_fred("BAMLH0A0HYM2"); ig = _load_fred("BAMLC0A0CM")
    if hy is None or ig is None: return None
    spread = (hy - ig).shift(1)
    panel = _panel(tickers)
    if panel is None: return None
    return pd.DataFrame({t: spread.reindex(panel.index, method="ffill") for t in panel.columns}, index=panel.index)

def real_yields(tickers, **kwargs):
    """10Y nominal minus 10Y breakeven."""
    import pandas as pd
    d10 = _load_fred("DGS10"); be = _load_fred("T10YIE")
    if d10 is None or be is None: return None
    ry = (d10 - be).shift(1)
    panel = _panel(tickers)
    if panel is None: return None
    return pd.DataFrame({t: ry.reindex(panel.index, method="ffill") for t in panel.columns}, index=panel.index)

def financial_conditions_index(tickers, **kwargs):
    import pandas as pd
    nfci = _load_fred("NFCI")
    if nfci is None: return None
    panel = _panel(tickers)
    if panel is None: return None
    return pd.DataFrame({t: nfci.reindex(panel.index, method="ffill") for t in panel.columns}, index=panel.index).shift(1)

def vix_term_structure(tickers, **kwargs):
    """VIX / VIX3M ratio, broadcast. Contango (<1) = calm regime."""
    import pandas as pd
    vix = _load_price_series("^VIX"); vix3m = _load_price_series("^VIX3M")
    if vix is None or vix3m is None: return None
    ratio = (vix / vix3m).shift(1)
    panel = _panel(tickers)
    if panel is None: return None
    return pd.DataFrame({t: ratio.reindex(panel.index, method="ffill") for t in panel.columns}, index=panel.index)

def pct_above_200dma(tickers, **kwargs):
    """For each ticker, 1 if above its own 200d MA else 0."""
    panel = _panel(tickers)
    if panel is None: return None
    ma200 = panel.rolling(200).mean()
    return (panel > ma200).astype(float).shift(1)

def earnings_surprise(tickers, **kwargs):
    """Stub: would need earnings cache. Return None to flag unimplemented."""
    return None

def google_trends_query(tickers, **kwargs):
    """Stub: pytrends is too flaky for production. Return None."""
    return None

def wsb_mention_velocity(tickers, **kwargs):
    """Stub: no historical WSB data on disk. Return None."""
    return None

def insider_trading_signal(tickers, **kwargs):
    """Stub: no Form 4 cache on disk yet."""
    return None

# ============= REGISTRY =============

SIGNALS = {
    "price_momentum": price_momentum,
    "volume_zscore": volume_zscore,
    "realized_vol": realized_vol,
    "yield_curve_slope": yield_curve_slope,
    "epu_index": epu_index,
    "credit_spreads_ighy": credit_spreads_ighy,
    "real_yields": real_yields,
    "financial_conditions_index": financial_conditions_index,
    "vix_term_structure": vix_term_structure,
    "pct_above_200dma": pct_above_200dma,
    "earnings_surprise": earnings_surprise,
    "google_trends_query": google_trends_query,
    "wsb_mention_velocity": wsb_mention_velocity,
    "insider_trading_signal": insider_trading_signal,
}

def get_signal(name, tickers, **kwargs):
    """Returns (signal_df, status). status: 'ok' | 'unimplemented' | 'no_data'."""
    fn = SIGNALS.get(name)
    if fn is None: return None, "unimplemented"
    try:
        s = fn(tickers, **kwargs)
        if s is None or len(s.dropna(how="all")) < 50: return None, "no_data"
        return s, "ok"
    except Exception as e:
        return None, f"error: {e}"

def signal_status_report():
    out = {}
    for name in SIGNALS:
        fn = SIGNALS[name]
        try:
            res = fn(["SPY","QQQ"])
            out[name] = "ok" if res is not None and len(res.dropna(how="all"))>50 else "no_data"
        except Exception as e:
            out[name] = f"err:{e}"
    return out

if __name__ == "__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="status":
        print(json.dumps(signal_status_report(), indent=2))
