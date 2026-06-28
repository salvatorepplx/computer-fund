#!/usr/bin/env python3
"""Throwaway robustness probe for the RDDT lead-lag EDGE (Blocker A suspicion check).

Question (per HANDOFF_CONTEXT_V2): the RDDT EDGE appeared right after the #46/#47
scorer-bias fixes changed the signal mid-series, and the tail has a ~15% price-proxy
spike (192.72 vs ~167 neighbors). Is the surviving permutation edge a transient
artifact of (a) the noisy tail price point and/or (b) the non-stationary scorer?

This does NOT touch live state, broker, or trade paths. Pure offline diagnostic on the
committed canonical series. Read-only.
"""
import json, random, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from evals.leadlag_permutation import _spaced_points, _best_poslag_corr, permutation_test


def perm_on(pairs, k=2000, seed=7, max_lag=5):
    """Replicate the permutation test on an explicit list of (dsent_level, price) spaced points."""
    # _spaced_points returns (sentiment_level, price) tuples; the eval diffs them internally.
    # We mirror the eval's internal math: build dsent / dret series, observed best pos-lag corr,
    # then shuffle sentiment labels k times.
    if len(pairs) < 3:
        return None
    sent = [p[0] for p in pairs]
    price = [p[1] for p in pairs]
    dsent = [sent[i] - sent[i-1] for i in range(1, len(sent))]
    dret = [price[i] - price[i-1] for i in range(1, len(price))]
    obs = _best_poslag_corr(dsent, dret, max_lag=max_lag)
    rng = random.Random(seed)
    ge = 0
    for _ in range(k):
        shuf = dsent[:]
        rng.shuffle(shuf)
        c = _best_poslag_corr(shuf, dret, max_lag=max_lag)
        if abs(c) >= abs(obs):
            ge += 1
    return {"n_pairs": len(pairs), "obs_best_poslag_corr": round(obs, 4),
            "p_value": round(ge / k, 4), "sig_at_0.10": (ge / k) <= 0.10}


pts = _spaced_points("TICKER:RDDT")
print(f"baseline n_spaced = {len(pts)}")
print(f"prices in spaced series: min={min(p[1] for p in pts)} median={statistics.median(p[1] for p in pts)} max={max(p[1] for p in pts)}")
print()

base = perm_on(pts, seed=7)
print("[A] BASELINE (all spaced points):", json.dumps(base))

# [B] Drop the single worst price-spike point (the one furthest from the running median)
med = statistics.median(p[1] for p in pts)
spike_idx = max(range(len(pts)), key=lambda i: abs(pts[i][1] - med))
print(f"\n[B] worst price-deviation point at idx {spike_idx}: price={pts[spike_idx][1]} (median {med})")
no_spike = [p for i, p in enumerate(pts) if i != spike_idx]
print("    edge WITHOUT the price spike:", json.dumps(perm_on(no_spike, seed=7)))

# [C] Drop the last 2 tail points (captured under the new scorer + noisy prices)
print("\n[C] edge WITHOUT last 2 tail points:", json.dumps(perm_on(pts[:-2], seed=7)))

# [D] Drop the last 4 tail points
print("[D] edge WITHOUT last 4 tail points:", json.dumps(perm_on(pts[:-4], seed=7)))

# [E] Winsorize prices to +/-5% of running median (kill obvious extraction spikes)
def winsor(pairs, frac=0.05):
    m = statistics.median(p[1] for p in pairs)
    out = []
    for s, pr in pairs:
        lo, hi = m * (1 - frac), m * (1 + frac)
        out.append((s, min(hi, max(lo, pr))))
    return out
print("\n[E] edge with prices winsorized to +/-5% of median:", json.dumps(perm_on(winsor(pts), seed=7)))
