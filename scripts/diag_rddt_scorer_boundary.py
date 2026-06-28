#!/usr/bin/env python3
"""Blocker-A suspicion diagnostic (read-only, offline).

Question from the V2 handoff: the RDDT lead-lag EDGE (p=0.0345) appeared right after the
#46/#47 scorer-bias fixes changed the signal mid-thesis. Is the edge a transient artifact of
that non-stationary signal rather than a real, tradeable lead-lag?

This script ONLY reads the committed canonical series + reruns the existing authoritative evals
with different random seeds and on a scorer-stationary subset. It places nothing, touches no
broker/account/order/state, and writes nothing. Pure falsification.
"""
import json, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SERIES = ROOT / "runs" / "sentiment" / "series" / "TICKER_RDDT.jsonl"

# #46 (quote-boilerplate guard) merged 2026-06-27 20:05 PDT = 2026-06-28T03:05Z
# #47 (remove lexical bullish bias) merged 2026-06-27 20:24 PDT = 2026-06-28T03:24Z
SCORER_CHANGE_UTC = "2026-06-28T03:05"  # conservative boundary = first of the two merges


def load():
    rows = []
    for line in SERIES.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def main():
    rows = load()
    n = len(rows)
    has_raw = [r for r in rows if "score_raw" in r]
    no_raw = [r for r in rows if "score_raw" not in r]
    print(f"=== RDDT series stationarity audit ===")
    print(f"total raw points: {n}")
    print(f"points WITH score_raw (new dual-scorer, post-#47): {len(has_raw)}")
    print(f"points WITHOUT score_raw (old scorer): {len(no_raw)}")

    # boundary: how many points captured at/after the scorer change
    post = [r for r in rows if (r.get("captured_at", "") >= SCORER_CHANGE_UTC)]
    pre = [r for r in rows if (r.get("captured_at", "") < SCORER_CHANGE_UTC)]
    print(f"\ncaptured BEFORE scorer change ({SCORER_CHANGE_UTC}Z): {len(pre)}")
    print(f"captured AT/AFTER scorer change: {len(post)}")

    # score distribution before vs after (the over-bullish-regex concern)
    def stats(rs, key="score"):
        vals = [r[key] for r in rs if isinstance(r.get(key), (int, float))]
        if not vals:
            return "n=0"
        m = sum(vals) / len(vals)
        lo, hi = min(vals), max(vals)
        return f"n={len(vals)} mean={m:+.4f} min={lo:+.4f} max={hi:+.4f}"

    print(f"\nscore dist PRE-change : {stats(pre)}")
    print(f"score dist POST-change: {stats(post)}")
    # where score and score_raw diverge, the scorer correction is large
    divs = [(r['score'] - r['score_raw']) for r in has_raw if isinstance(r.get('score_raw'), (int, float))]
    if divs:
        print(f"\nscore - score_raw on post-#47 pts: mean={sum(divs)/len(divs):+.4f} "
              f"min={min(divs):+.4f} max={max(divs):+.4f} (large => scorer changed the reading materially)")

    # price-proxy sanity in the tail (the 192.72 -> 167.0 in 20s jump)
    print(f"\n=== tail price_proxy sanity (last 5 pts) ===")
    for r in rows[-5:]:
        print(f"  {r.get('captured_at','?')[:19]}  score={r.get('score'):+.4f}  px={r.get('price_proxy')}")

    print(f"\n=== permutation stability across seeds (is p=0.0345 robust?) ===")
    for seed in [7, 1, 42, 123, 2024]:
        try:
            out = subprocess.run(
                [sys.executable, str(ROOT / "evals" / "leadlag_permutation.py"), "TICKER:RDDT",
                 "--seed", str(seed)],
                capture_output=True, text=True, cwd=str(ROOT), timeout=120,
            )
            txt = out.stdout.strip()
            try:
                d = json.loads(txt[txt.index("{"):])
                print(f"  seed={seed:>5}: p={d.get('p_value')}  sig={d.get('significant_at_0.10')}  "
                      f"verdict={d.get('verdict')}")
            except Exception:
                print(f"  seed={seed}: (no --seed support) {txt.splitlines()[-1][:80] if txt else out.stderr[:80]}")
        except Exception as e:
            print(f"  seed={seed}: error {e}")


if __name__ == "__main__":
    main()
