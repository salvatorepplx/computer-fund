"""
Lead-lag probe on the REAL captured series (Computer Fund).

Tests the core thesis directly: do sentiment CHANGES lead price CHANGES?
For each candidate lag L (sentiment at t vs price-return at t+L), compute the
Pearson correlation of d(sentiment) vs d(price). A real predate edge shows the
best correlation at a POSITIVE lag (sentiment moves first) and clears a
magnitude bar. Negative/zero best-lag = coincident or lagging = NO edge.

This is honest about its own limits:
- Reports N and whether N meets the authoritative minimum (default 24).
- Below the minimum it still prints a PRELIMINARY, explicitly non-authoritative read.
- Differences (returns) are used, not levels, to avoid spurious trend correlation.

Usage: python evals/leadlag_real.py TICKER:NVDA [--min-n 24] [--max-lag 5]
"""
from __future__ import annotations
import sys, json, argparse, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from execution.ingest_runner import load_series


def _pearson(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    ca = [x - ma for x in a]
    cb = [x - mb for x in b]
    num = sum(x * y for x, y in zip(ca, cb))
    da = math.sqrt(sum(x * x for x in ca))
    db = math.sqrt(sum(y * y for y in cb))
    return num / (da * db) if da and db else 0.0


def _diffs(xs: list[float]) -> list[float]:
    return [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]


def probe(entity: str, min_n: int = 24, max_lag: int = 5,
          min_corr: float = 0.30) -> dict:
    series = load_series(entity)
    # Prefer the unsmoothed raw score (more responsive -> better lead-lag signal);
    # fall back to the EWMA score for older points captured before score_raw existed.
    def _sent(p):
        v = p.get("score_raw")
        return v if v is not None else p.get("score")

    # Keep only points with both sentiment and a real price.
    valid = [p for p in series
             if _sent(p) is not None and p.get("price_proxy") is not None]

    # TIME-SPACING: collapse burst/near-duplicate captures so each retained point
    # is a genuine time-spaced observation. Burst points (many in seconds) create
    # fake stationary pairs that corrupt the lead-lag. Keep the LAST point in each
    # cluster separated by >= min_gap_s seconds.
    import datetime as _dt
    def _t(p):
        try:
            return _dt.datetime.fromisoformat(p.get("ts").replace("Z", "+00:00"))
        except Exception:
            return None
    min_gap_s = 180.0  # 3 min: anything closer is a burst duplicate, not new info
    spaced = []
    last_t = None
    for p in sorted(valid, key=lambda r: r.get("ts", "")):
        t = _t(p)
        if t is None:
            continue
        if last_t is None or (t - last_t).total_seconds() >= min_gap_s:
            spaced.append(p)
            last_t = t
        else:
            spaced[-1] = p  # replace: keep most recent in this burst cluster
            last_t = t
    pts = [(_sent(p), p.get("price_proxy")) for p in spaced]
    n_raw = len(valid)
    n = len(pts)
    if n < 3:
        return {"entity": entity, "n": n, "verdict": "INSUFFICIENT",
                "authoritative": False, "note": "need >=3 aligned points"}

    sent = [s for s, _ in pts]
    price = [pr for _, pr in pts]
    dsent = _diffs(sent)
    dret = _diffs(price)  # absolute price change; sign is what matters for lead-lag

    lags = []
    for lag in range(-max_lag, max_lag + 1):
        # positive lag: sentiment change at t vs price change at t+lag
        if lag >= 0:
            end = min(len(dsent), len(dret) - lag)
            a = dsent[:end]
            b = dret[lag:lag + end]
        else:
            off = -lag
            end = min(len(dsent) - off, len(dret))
            a = dsent[off:off + end]
            b = dret[:end]
        if len(a) >= 2:
            lags.append({"lag": lag, "corr": round(_pearson(a, b), 4), "n_pairs": len(a)})

    if not lags:
        return {"entity": entity, "n": n, "verdict": "INSUFFICIENT",
                "authoritative": False, "note": "not enough diff pairs"}

    # Circularity guard: if sentiment LEVEL tracks price LEVEL contemporaneously
    # too tightly, the "signal" may just be reading price action back (lookahead-ish).
    # Flag it so a high-corr name cannot quietly graduate to an EDGE verdict.
    _ms = sum(sent) / len(sent); _mp = sum(price) / len(price)
    _cs = [x - _ms for x in sent]; _cp = [x - _mp for x in price]
    _den = (sum(a * a for a in _cs) * sum(b * b for b in _cp)) ** 0.5
    contemp_corr = round((sum(a * b for a, b in zip(_cs, _cp)) / _den), 4) if _den else 0.0
    circularity_flag = abs(contemp_corr) >= 0.6

    best = max(lags, key=lambda r: (r["corr"], r["lag"]))
    authoritative = n >= min_n
    # Edge requires: best correlation at positive lead, clearing magnitude bar.
    edge = best["lag"] >= 1 and best["corr"] >= min_corr and not circularity_flag

    if not authoritative:
        verdict = "PRELIMINARY_EDGE" if edge else "PRELIMINARY_NO_EDGE"
    else:
        verdict = "EDGE" if edge else "KILL"

    return {
        "entity": entity, "n": n, "n_raw_points": n_raw, "min_n": min_n, "authoritative": authoritative,
        "verdict": verdict, "best_lag": best["lag"], "best_corr": best["corr"],
        "min_corr": min_corr, "contemp_corr": contemp_corr, "circularity_flag": circularity_flag, "all_lags": lags,
        "note": ("Authoritative read." if authoritative else
                 f"PRELIMINARY only: N={n} < {min_n}. Not a basis for capital."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("entity", nargs="?", default="TICKER:NVDA")
    ap.add_argument("--min-n", type=int, default=24)
    ap.add_argument("--max-lag", type=int, default=5)
    ap.add_argument("--min-corr", type=float, default=0.30)
    a = ap.parse_args()
    print(json.dumps(probe(a.entity, a.min_n, a.max_lag, a.min_corr), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
