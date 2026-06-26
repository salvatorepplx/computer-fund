"""
Permutation (null) test for the lead-lag edge on REAL series.

The lead-lag probe finds the best correlation between d(sentiment) and d(price)
across lags. With small N, a high correlation can arise by pure chance. This test
asks the honest question: is the REAL best-lag correlation better than what random
shuffles of the sentiment labels produce against the SAME real price path?

Method (uses the same time-spacing + raw-score selection as leadlag_real):
  1. Build the real spaced (sentiment, price) series.
  2. Compute the observed statistic: max positive-lag |corr| of d(sent) vs d(price).
  3. Shuffle the sentiment series K times (price path fixed), recompute the stat.
  4. p = fraction of shuffles whose stat >= observed. Low p => edge unlikely by chance.

A real edge should have a LOW p-value (<= 0.10). This is a stronger, honest gate
than a raw correlation threshold and complements the circularity guard. It only
becomes authoritative at the same N>=24 floor; below that it is PRELIMINARY.
"""
from __future__ import annotations
import sys, json, argparse, random, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from execution.ingest_runner import load_series
from evals.leadlag_real import _pearson, _diffs


def _spaced_points(entity: str, min_gap_s: float = 180.0):
    series = load_series(entity)
    def _sent(p):
        v = p.get("score_raw")
        return v if v is not None else p.get("score")
    valid = [p for p in series if _sent(p) is not None and p.get("price_proxy") is not None]
    spaced, last_t = [], None
    for p in sorted(valid, key=lambda r: r.get("ts", "")):
        try:
            t = dt.datetime.fromisoformat(p.get("ts").replace("Z", "+00:00"))
        except Exception:
            continue
        if last_t is None or (t - last_t).total_seconds() >= min_gap_s:
            spaced.append(p); last_t = t
        else:
            spaced[-1] = p; last_t = t
    return [(_sent(p), p["price_proxy"]) for p in spaced]


def _best_poslag_corr(dsent, dret, max_lag=5):
    best = 0.0
    for lag in range(1, max_lag + 1):  # positive lags only: sentiment must LEAD
        end = min(len(dsent), len(dret) - lag)
        if end >= 2:
            c = abs(_pearson(dsent[:end], dret[lag:lag + end]))
            best = max(best, c)
    return best


def permutation_test(entity: str, k: int = 2000, max_lag: int = 5,
                     min_n: int = 24, seed: int = 7) -> dict:
    pts = _spaced_points(entity)
    n = len(pts)
    if n < 4:
        return {"entity": entity, "n": n, "verdict": "INSUFFICIENT",
                "authoritative": False, "note": "need >=4 spaced points"}
    sent = [s for s, _ in pts]
    price = [p for _, p in pts]
    dret = _diffs(price)
    observed = _best_poslag_corr(_diffs(sent), dret, max_lag)

    rng = random.Random(seed)
    ge = 0
    for _ in range(k):
        sh = sent[:]
        rng.shuffle(sh)
        stat = _best_poslag_corr(_diffs(sh), dret, max_lag)
        if stat >= observed - 1e-12:
            ge += 1
    p_value = ge / k
    authoritative = n >= min_n
    significant = p_value <= 0.10
    if not authoritative:
        verdict = "PRELIMINARY_SIGNIFICANT" if significant else "PRELIMINARY_NULL"
    else:
        verdict = "EDGE_SURVIVES_NULL" if significant else "EDGE_IS_NOISE"
    return {"entity": entity, "n": n, "min_n": min_n, "authoritative": authoritative,
            "observed_best_poslag_corr": round(observed, 4),
            "p_value": round(p_value, 4), "k_shuffles": k,
            "significant_at_0.10": significant, "verdict": verdict,
            "note": ("Authoritative permutation read." if authoritative
                     else f"PRELIMINARY: N={n}<{min_n}. Not a basis for capital.")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("entity", nargs="?", default="TICKER:NVDA")
    ap.add_argument("--k", type=int, default=2000)
    ap.add_argument("--max-lag", type=int, default=5)
    a = ap.parse_args()
    print(json.dumps(permutation_test(a.entity, a.k, a.max_lag), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
