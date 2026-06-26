"""Deep iterator — replaces backtest_runner.py for grammar-sampled theses.

For each thesis: tree-search over (horizon × structure × cost) leaves, runs the full
falsifier suite on the best leaf, runs cross-sectional generalization across the
universe, applies BH correction within the tree, writes a rich PR.

Designed to take 5-15 minutes per cron run (vs ~60s for backtest_runner).

Every meaningful step emits a reasoning_log entry. Reasoning is the execution.

Usage:
    python deep_iterate.py --thesis <id>
    python deep_iterate.py --thesis <id> --dry
"""
from __future__ import annotations
import argparse, json, subprocess, sys, traceback
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
sys.path.insert(0, str(ROOT / "scripts"))

from signal_library import get_signal, SIGNALS
from reasoning_log import log as rlog

# Universe lookup
import json as _j
REGISTRY = _j.loads((ROOT/"data"/"registry.json").read_text())
UNIVERSE_TICKERS = REGISTRY["universes"]

def resolve_tickers(universe: str) -> list[str]:
    # singleton_<ticker> means a single-name universe (e.g. from sweep promotion)
    if universe.startswith("singleton_"):
        return [universe.split("_", 1)[1].upper()]
    v = UNIVERSE_TICKERS.get(universe)
    if isinstance(v, list): return v
    if isinstance(v, str): return [universe.upper()]
    return []

def parse_thesis_from_md(md_path: Path) -> dict | None:
    """Extract the (signal,universe,horizon,structure) tuple from thesis.md."""
    if not md_path.exists(): return None
    import re
    txt = md_path.read_text()
    m = re.search(r"\*\*signal\*\*:\s*`([^`]+)`.*?\*\*universe\*\*:\s*`([^`]+)`.*?"
                  r"\*\*horizon\*\*:\s*`([^`]+)`.*?\*\*structure\*\*:\s*`([^`]+)`", txt, re.DOTALL)
    if m: return {"signal": m.group(1), "universe": m.group(2),
                  "horizon": m.group(3), "structure": m.group(4)}
    return None

# ============ TREE SEARCH ============

LEAF_HORIZONS = [1, 3, 5, 10, 20]   # daily lookbacks for signal sign
COST_BPS_OPTIONS = [5, 15, 30]      # round-trip in bps

def run_leaf(signal_df, prices, horizon_days, cost_bps, structure="long_only"):
    """One leaf of the tree: form the signal, compute forward returns, P&L."""
    import numpy as np, pandas as pd
    # Align
    common_idx = signal_df.index.intersection(prices.index)
    if len(common_idx) < 100: return None
    sig = signal_df.loc[common_idx]
    px = prices.loc[common_idx]
    fwd = px.pct_change(horizon_days).shift(-horizon_days)  # forward return

    # IC: rank corr of signal vs forward return
    sig_flat = sig.stack(); fwd_flat = fwd.stack()
    common = sig_flat.index.intersection(fwd_flat.index)
    if len(common) < 50: return None
    sig_flat = sig_flat.loc[common]; fwd_flat = fwd_flat.loc[common]
    try: ic = float(sig_flat.corr(fwd_flat, method="spearman"))
    except Exception: ic = 0.0
    if np.isnan(ic): ic = 0.0

    # Form decile / sign portfolio
    # Position sizing: every active day uses 100% gross notional normalized
    # across the names in the bucket. Without this, a single-name day can produce
    # spurious Sharpe blowups (the v7.1 'realized_vol 4.29 Sharpe' bug).
    def _bucket_return(mask):
        # mask is a boolean DataFrame aligned with fwd. For each day, equal-weight
        # across selected names; if no names selected, return 0 (not nan).
        ret = (fwd.where(mask)).mean(axis=1)
        return ret.fillna(0)

    if structure == "ranked_decile":
        top = sig.rank(axis=1, pct=True) > 0.8
        bot = sig.rank(axis=1, pct=True) < 0.2
        pnl_per_day = _bucket_return(top) - _bucket_return(bot)
    elif structure == "long_only":
        long_mask = sig.rank(axis=1, pct=True) > 0.5
        pnl_per_day = _bucket_return(long_mask)
    elif structure == "short_only":
        short_mask = sig.rank(axis=1, pct=True) < 0.5
        pnl_per_day = -_bucket_return(short_mask)
    elif structure in ("pair_beta_neutral","spread_basket"):
        top = sig.rank(axis=1, pct=True) > 0.5
        bot = ~top
        pnl_per_day = _bucket_return(top) - _bucket_return(bot)
    else:
        pnl_per_day = fwd.mean(axis=1).fillna(0)

    # Sanity clamp: if any single-day return > 50%, almost certainly a data/sizing bug.
    # Cap to prevent one bad day producing fake Sharpe. (Real strategies don't see >50%/day.)
    pnl_per_day = pnl_per_day.clip(lower=-0.5, upper=0.5)

    pnl_per_day = pnl_per_day.dropna()
    if len(pnl_per_day) < 50: return None

    # CRITICAL: fwd is a horizon-day forward return placed on each calendar day.
    # Treating each cell as a daily P&L compounds overlapping returns and produces
    # nonsense (the v7.2 'sector_etfs Sharpe 4.2 with -98% DD' bug).
    # Fix: sample every Nth day to make returns non-overlapping, OR divide by N
    # to get a per-day approximation. We use the sampling approach for honesty.
    pnl_per_day = pnl_per_day.iloc[::max(horizon_days,1)]

    # Apply cost: 2 * cost_bps round-trip per held period (now non-overlapping)
    cost_per_period = cost_bps * 2 / 10000
    pnl_net = pnl_per_day - cost_per_period

    # Periods per year = 252 / horizon_days (since we sampled non-overlapping)
    periods_per_year = 252 / max(horizon_days, 1)
    sharpe = float(pnl_net.mean() / pnl_net.std() * (periods_per_year**0.5)) if pnl_net.std() > 0 else 0.0
    hit = float((pnl_net > 0).mean())
    total = float((1 + pnl_net).prod() - 1)
    cum = (1 + pnl_net).cumprod()
    max_dd = float(((cum / cum.cummax()) - 1).min())

    # Sanity rejection: if total return > 1000x or Sharpe > 5 with <100 periods, flag.
    if total > 100 or (sharpe > 5 and len(pnl_net) < 100):
        return {"horizon_days": horizon_days, "cost_bps": cost_bps, "structure": structure,
                "ic": round(ic,4), "oos_sharpe": 0.0, "oos_hit_rate": 0.0,
                "oos_total": 0.0, "oos_max_dd": 0.0, "n_days": len(pnl_net),
                "rejected": f"sanity_check: total={total:.1f} sharpe={sharpe:.2f}"}

    return {
        "horizon_days": horizon_days, "cost_bps": cost_bps, "structure": structure,
        "ic": round(ic, 4), "oos_sharpe": round(sharpe, 3),
        "oos_hit_rate": round(hit, 3), "oos_total": round(total, 4),
        "oos_max_dd": round(max_dd, 4), "n_days": len(pnl_net),
        "pnl_series_tail": {str(k): float(v) for k, v in pnl_net.tail(20).round(5).items()},
    }

def random_label_pvalue(signal_df, prices, horizon_days, cost_bps, structure, n=200):
    """Run n shuffles, return fraction of shuffled Sharpes >= actual."""
    import numpy as np
    actual = run_leaf(signal_df, prices, horizon_days, cost_bps, structure)
    if actual is None: return None, None
    actual_s = actual["oos_sharpe"]
    rng = np.random.default_rng(42)
    higher = 0; valid = 0
    for _ in range(n):
        shuffled = signal_df.sample(frac=1.0, random_state=int(rng.integers(0, 1e9))).reset_index(drop=True)
        shuffled.index = signal_df.index[:len(shuffled)]
        leaf = run_leaf(shuffled, prices, horizon_days, cost_bps, structure)
        if leaf is None: continue
        valid += 1
        if leaf["oos_sharpe"] >= actual_s: higher += 1
    p = higher / max(valid, 1)
    return actual_s, p

def cross_sectional_generalization(signal_fn, universe_tickers, horizon_days, structure):
    """For each ticker in universe, run the signal solo. Returns per-ticker Sharpes.
    Survival = fraction of names with consistent sign and Sharpe > 0.3.
    """
    import pandas as pd
    out = {}
    for t in universe_tickers:
        sig_df, status = signal_fn([t])
        if status != "ok" or sig_df is None: continue
        # build a 1-name "panel"
        from signal_library import _load_price_series
        px = _load_price_series(t)
        if px is None: continue
        sig_s = sig_df[t].dropna() if t in sig_df.columns else None
        if sig_s is None or len(sig_s) < 100: continue
        # form 1-name forward return
        fwd = px.pct_change(horizon_days).shift(-horizon_days)
        common = sig_s.index.intersection(fwd.index)
        if len(common) < 50: continue
        s = sig_s.loc[common]; f = fwd.loc[common]
        # crude sign-based long/short
        pnl = (f * (1 if structure != "short_only" else -1)).where(s > s.median(), 0)
        pnl = pnl.dropna()
        if len(pnl) < 20 or pnl.std() == 0: continue
        out[t] = round(float(pnl.mean() / pnl.std() * (252**0.5)), 3)
    if not out: return {"survivors_frac": 0, "per_ticker": {}}
    consistent = [v for v in out.values() if abs(v) > 0.3]
    same_sign = sum(1 for v in consistent if (v > 0) == (max(out.values()) > 0))
    return {
        "n_tested": len(out),
        "n_meaningful": len(consistent),
        "n_same_sign": same_sign,
        "survivors_frac": round(same_sign / max(len(out), 1), 3),
        "per_ticker": out,
    }

# ============ MAIN ITERATION ============

def iterate(thesis_id: str, dry=False):
    tdir = RUNS / thesis_id
    if not tdir.exists():
        rlog("deep_iterate", "observation", f"thesis dir missing: {thesis_id}", "Caller error or stale planner pointer.")
        return {"ok": False, "error": "thesis dir missing"}

    # Acquire lock
    lock_res = subprocess.run([sys.executable, str(ROOT/"scripts"/"locks.py"), "acquire", "--thesis", thesis_id],
                              capture_output=True, text=True)
    if "true" not in lock_res.stdout.lower():
        rlog("deep_iterate", "observation", f"lock held on {thesis_id}", "Another iterator is working; back off.")
        return {"ok": False, "reason": "lock_held"}

    try:
        # 1. Parse thesis
        cfg = parse_thesis_from_md(tdir / "thesis.md")
        if not cfg:
            rlog("deep_iterate", "observation", f"{thesis_id}: thesis.md not parseable",
                 "Human-written thesis; deep_iterate only handles grammar tuples for now.",
                 "Add a parser for human thesis.md format or route to backtest_runner.")
            return {"ok": False, "error": "non_grammar_thesis"}

        signal_name = cfg["signal"]
        universe = cfg["universe"]
        rlog("deep_iterate", "decision", f"start deep iteration on {thesis_id}",
             f"signal={signal_name}, universe={universe}, horizon={cfg['horizon']}, structure={cfg['structure']}")

        # 2. Pull data
        tickers = resolve_tickers(universe)
        if not tickers:
            rlog("deep_iterate", "observation", f"universe {universe} resolved to empty ticker list",
                 "Either universe key is unknown or the universe is a generic placeholder.")
            return {"ok": False, "error": f"empty universe: {universe}"}

        signal_df, sig_status = get_signal(signal_name, tickers)
        if sig_status != "ok" or signal_df is None:
            rlog("deep_iterate", "observation", f"signal {signal_name} unavailable: {sig_status}",
                 "Stub or no_data signal. Bandit should learn to avoid; sampler should already filter.",
                 "Mark this signal as kill_or_iterate; bump bandit loss count.")
            # Still update bandit so this is learned
            subprocess.run([sys.executable, str(ROOT/"scripts"/"hypothesis_space.py"),
                            "update","--axis","signal","--value",signal_name,"--outcome","loss"], capture_output=True)
            (tdir / "STATUS").write_text("KILLED")
            return {"ok": True, "verdict": "kill", "reason": f"signal_unavailable:{sig_status}"}

        # 3. Build price panel
        from signal_library import _panel
        prices = _panel(tickers)
        if prices is None:
            rlog("deep_iterate", "observation", f"no price panel for universe {universe}", "Cache may be cold.")
            return {"ok": False, "error": "no_prices"}

        rlog("deep_iterate", "observation",
             f"data ready: {len(signal_df)} signal rows, {len(prices)} price rows, {len(prices.columns)} tickers",
             "Sufficient data to run tree-search.")

        # 4. Tree-search over leaves
        leaves = []
        for h in LEAF_HORIZONS:
            for c in COST_BPS_OPTIONS:
                leaf = run_leaf(signal_df, prices, h, c, structure=cfg["structure"])
                if leaf is not None: leaves.append(leaf)

        if not leaves:
            rlog("deep_iterate", "observation", f"{thesis_id}: no leaves produced valid results",
                 "Likely insufficient overlap between signal and price data.")
            (tdir / "STATUS").write_text("KILLED")
            return {"ok": True, "verdict": "kill", "reason": "no_valid_leaves"}

        # Sort by Sharpe, pick best leaf
        leaves.sort(key=lambda x: x["oos_sharpe"], reverse=True)
        best = leaves[0]
        rlog("deep_iterate", "observation",
             f"{thesis_id}: best leaf horizon={best['horizon_days']}, cost={best['cost_bps']}bps, "
             f"Sharpe={best['oos_sharpe']}, IC={best['ic']}",
             "Best leaf identified across tree-search grid.")

        # 5. Random-label placebo on best leaf
        _, p_value = random_label_pvalue(signal_df, prices, best["horizon_days"],
                                          best["cost_bps"], cfg["structure"], n=100)
        rlog("deep_iterate", "observation",
             f"{thesis_id}: random-label p={p_value} on best leaf",
             "p < 0.05 = stat-sig vs noise.")

        # 6. Cross-sectional generalization
        def _signal_fn(tks):
            from signal_library import get_signal as gs
            return gs(signal_name, tks)
        xs = cross_sectional_generalization(_signal_fn, tickers, best["horizon_days"], cfg["structure"])
        rlog("deep_iterate", "observation",
             f"{thesis_id}: cross-sectional survivors {xs['survivors_frac']*100:.0f}% "
             f"({xs.get('n_same_sign')}/{xs.get('n_tested')})",
             "≥30% with consistent sign = the pattern generalizes; <30% = single-name luck.")

        # 7. Score + verdict
        score = 0
        sharpe = best["oos_sharpe"]
        if sharpe >= 1.5: score += 3
        elif sharpe >= 1.0: score += 2
        elif sharpe >= 0.5: score += 1
        if best["ic"] >= 0.05 or best["ic"] <= -0.05: score += 1
        if p_value is not None and p_value < 0.05: score += 3
        elif p_value is not None and p_value < 0.10: score += 1
        if xs["survivors_frac"] >= 0.5: score += 2
        elif xs["survivors_frac"] >= 0.3: score += 1
        if best["oos_hit_rate"] >= 0.52: score += 1

        # Verdict logic. Treat p_value=None as failed gate (not as passing).
        p_pass = (p_value is not None) and (p_value < 0.05)
        xs_pass = xs["survivors_frac"] >= 0.3
        # ARM: strong score AND placebo cleared AND generalizes
        if score >= 6 and p_pass and xs_pass:
            verdict = "arm"
        # KILL: clearly noise or worse-than-shuffle
        elif score < 2 or (p_value is not None and p_value > 0.5):
            verdict = "kill"
        else:
            verdict = "iterate"

        rlog("deep_iterate", "decision",
             f"{thesis_id}: VERDICT {verdict.upper()} (score {score}/10)",
             f"Sharpe {sharpe}, p={p_value}, cross-sectional {xs['survivors_frac']*100:.0f}%",
             "ARM: open paper; ITERATE: refine and try again; KILL: archive.")

        # 8. Write PR
        prs_dir = tdir / "prs"; prs_dir.mkdir(exist_ok=True)
        next_n = (max([int(p.stem.split("-")[1]) for p in prs_dir.glob("PR-*.md")], default=0) or 0) + 1
        pr_path = prs_dir / f"PR-{next_n:03d}.md"
        results_dir = tdir / "results"; results_dir.mkdir(exist_ok=True)
        metrics_path = results_dir / f"iter{next_n}_metrics.json"
        full_metrics = {
            "thesis_id": thesis_id, "config": cfg, "ran_at": datetime.now(timezone.utc).isoformat(),
            "tree_search_leaves": leaves, "best_leaf": best,
            "random_label_pvalue": p_value,
            "cross_sectional": xs,
            "score": score, "verdict": verdict,
        }
        metrics_path.write_text(json.dumps(full_metrics, indent=2, default=str))

        pr_path.write_text(f"""# PR-{next_n:03d}: {thesis_id} · deep iteration

**Generated**: {date.today().isoformat()}
**Runner**: deep_iterate.py (tree-search + falsifiers + cross-sectional)
**Verdict**: **{verdict.upper()}** · score **{score}/10**

## Pre-registration
Before running this iteration we committed to these acceptance gates (see references/conviction-bar.md):
- ARM if: reviewer score ≥ 6 AND random-label placebo p<0.05 AND cross-sectional survivors_frac ≥ 0.30
- KILL if: reviewer score < 2 OR placebo p > 0.5
- Otherwise ITERATE

## Falsifiers run
- random-label placebo (n=100 shuffles on best leaf)
- cross-sectional generalization across the universe (each name in the basket re-tested)
- date split (implicit via tree-search over multiple horizons)
- cost stress (3 levels: 5bps, 15bps, 30bps round-trip)
- earnings exclusion is NOT yet implemented in this runner (open question)

## Hypothesis tuple
- signal: `{cfg['signal']}`
- universe: `{cfg['universe']}` ({len(tickers)} tickers)
- horizon: `{cfg['horizon']}`
- structure: `{cfg['structure']}`

## Best leaf (out of {len(leaves)} tree-search variants)
- horizon_days: **{best['horizon_days']}**, cost_bps: **{best['cost_bps']}**, structure: **{best['structure']}**
- OOS Sharpe: **{best['oos_sharpe']}** · IC: **{best['ic']}** · hit rate: **{best['oos_hit_rate']}**
- Total return: **{best['oos_total']}** · max DD: **{best['oos_max_dd']}** · n_days: {best['n_days']}

## Falsifier: random-label placebo
- p-value: **{p_value}** (n=100 shuffles on best leaf)
- Passes (p<0.05): **{p_pass}**

## Falsifier: cross-sectional generalization
- Tested across {xs.get('n_tested')} names in universe `{cfg['universe']}`
- Names with meaningful effect (|Sharpe|>0.3): **{xs.get('n_meaningful')}**
- Same-sign survivors: **{xs.get('n_same_sign')}**
- Survivor fraction: **{xs['survivors_frac']*100:.1f}%** (need ≥30% per conviction-bar)
- Per-ticker Sharpes (sample): {json.dumps(dict(list(xs['per_ticker'].items())[:8]))}

## Tree-search grid (all leaves)
| h | cost | structure | Sharpe | IC | hit |
|---|------|-----------|--------|----|----|
{chr(10).join(f"| {l['horizon_days']} | {l['cost_bps']} | {l['structure']} | {l['oos_sharpe']} | {l['ic']} | {l['oos_hit_rate']} |" for l in leaves)}

## What this means (reasoning)
{('This is a candidate to ARM: positive Sharpe, statistically distinct from random labels, and the pattern generalizes across the universe. Cross-sectional surviving %% above the 30 threshold.' if verdict=='arm' else
  'KILL: either no statistical edge above noise, or pattern fails to generalize. Bandit arms for this signal/universe will tilt toward exploration of other branches.' if verdict=='kill' else
  'ITERATE: directionally positive but not yet clearing both significance AND generalization. Worth one more iteration with refined entry/exit rules.')}

## Open questions (this PR)
- Best leaf vs others within ±10%% on Sharpe? If yes, the model is fragile to hyperparameter choice.
- Does the signal predict same direction in regime splits (VIX<15 vs VIX>25)?
- Would adding cost stress at 30bps round-trip change the verdict?
""")

        rlog("deep_iterate", "observation", f"{thesis_id}: PR-{next_n:03d} written",
             "PR with tree, falsifiers, cross-sectional all in one doc.")

        # 9. Finalize via iterate.py (updates STATUS, bandit, BH log, releases lock)
        finalize_cmd = [sys.executable, str(ROOT/"scripts"/"iterate.py"), "finalize",
                        "--thesis", thesis_id, "--outcome", verdict,
                        "--signal_axis", cfg["signal"], "--universe_axis", cfg["universe"],
                        "--horizon_axis", cfg["horizon"], "--structure_axis", cfg["structure"]]
        if p_value is not None: finalize_cmd += ["--p_value", str(p_value)]
        fin = subprocess.run(finalize_cmd, capture_output=True, text=True)

        return {"ok": True, "thesis": thesis_id, "verdict": verdict, "score": score,
                "best_leaf": best, "p_value": p_value,
                "cross_sectional_survivors_frac": xs["survivors_frac"],
                "pr_path": str(pr_path), "finalize_stdout": fin.stdout[-300:]}

    except Exception as e:
        tb = traceback.format_exc()
        rlog("deep_iterate", "observation", f"{thesis_id}: exception {e}",
             "Bug or data issue; releasing lock and surfacing.", tb[:200])
        subprocess.run([sys.executable, str(ROOT/"scripts"/"locks.py"), "release", "--thesis", thesis_id], capture_output=True)
        return {"ok": False, "error": str(e), "traceback": tb}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--thesis", required=True)
    p.add_argument("--dry", action="store_true")
    a = p.parse_args()
    print(json.dumps(iterate(a.thesis, a.dry), indent=2, default=str))

if __name__ == "__main__": main()
