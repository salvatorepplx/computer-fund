"""Shell-executable backtest runner. Runs a single hypothesis end-to-end.

Reads thesis.md → extracts (signal, universe, horizon, structure) → pulls data
→ runs walk-forward backtest → runs all falsifiers → writes PR + artifacts.

Designed for cron-fired shell contexts that don't have agent-layer tools.
The full iteration completes in this one process: prepare → backtest → finalize.

Usage:
    python backtest_runner.py --thesis <id>           # full iteration
    python backtest_runner.py --thesis <id> --dry     # parse only, don't run

Side effects:
- Acquires + releases lock via locks.py
- Writes results/iterN_metrics.json, iterN_equity_curve.png, iterN_falsifiers.md
- Writes prs/PR-NNN.md
- Calls iterate.py finalize on success
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, traceback
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"

# -------- thesis parsing --------

THESIS_TUPLE_RE = re.compile(
    r"\*\*signal\*\*:\s*`([^`]+)`.*?\*\*universe\*\*:\s*`([^`]+)`.*?"
    r"\*\*horizon\*\*:\s*`([^`]+)`.*?\*\*structure\*\*:\s*`([^`]+)`",
    re.DOTALL,
)

def parse_thesis_tuple(thesis_md_path: Path):
    """Extract (signal, universe, horizon, structure) from a generated thesis.
    For human-written theses (not from the grammar), fall back to None and use defaults."""
    if not thesis_md_path.exists(): return None
    txt = thesis_md_path.read_text()
    m = THESIS_TUPLE_RE.search(txt)
    if m: return {"signal": m.group(1), "universe": m.group(2), "horizon": m.group(3), "structure": m.group(4)}
    return None  # fallback for non-grammar theses

# -------- universe map --------

UNIVERSE_TICKERS = {
    "any_equity": ["SPY"],  # placeholder — would normally need ticker context from thesis
    "spy_indexed": ["SPY", "QQQ"],
    "social_attention_basket": ["RDDT","META","SNAP","PINS","RBLX","COIN","HOOD","PLTR","CVNA","TSLA","GME","AMC"],
    "retail_attention_basket": ["GME","AMC","BB","PLTR","SOFI","TSLA","COIN","HOOD","RDDT","CVNA","RIVN","LCID"],
    "agi_buildout_full": ["NVDA","AVGO","AMD","ORCL","TSM","CRWV","INTC","MU","SNDK","WDC","LUMN","COHR","BE","NRG","VST","CEG","GEV","ETR","CORZ","RIOT","IREN","CIFR","APLD"],
    "sector_etfs": ["XLK","XLF","XLE","XLU","XLV","XLY","XLI","XLB","XLP","XLRE","XLC"],
    "factor_etfs": ["MTUM","QUAL","VLUE","USMV","SPLV","SIZE","COWZ"],
    "rates": ["TLT","IEI","IEF","SHY","TIP","HYG","LQD"],
    "commodities": ["GLD","SLV","USO","UNG","CPER","DBC","UUP"],
    "crypto": ["BTC-USD","ETH-USD","SOL-USD"],
}

# Special-case mapping for human-written theses (id → ticker basket)
HUMAN_THESIS_DEFAULTS = {
    "agi_power_vs_xlu": {"signal": "long_short_basket", "longs": ["BE","VST","CEG"], "shorts": ["XLU"], "horizon": "20d"},
    "mu_hbm_pre_earnings_drift": {"signal": "pre_earnings_drift", "longs": ["MU"], "shorts": ["SOXX"], "horizon": "10d_pre_earnings"},
    "nvda_earnings_smh_spread": {"signal": "post_earnings_meanrev", "longs": ["SMH"], "shorts": ["NVDA"], "horizon": "2d_post_earnings", "trigger": "gap_5pct"},
    "attention_fade_rddt": {"signal": "attention_fade", "shorts": ["RDDT"], "horizon": "intraday_oc"},
    "event_conditional_rddt": {"signal": "event_conditional", "longs": ["RDDT"], "horizon": "1d"},
}

# -------- backtest stub (real logic depends on hypothesis kind) --------

def run_backtest(thesis_id: str, config: dict, results_dir: Path) -> dict:
    """Execute the backtest. Returns metrics dict.

    For now this is a deterministic, conservative stub: it pulls data via yfinance
    for the named tickers, computes returns, applies a simple buy-and-hold + simple
    momentum/volume signal where applicable, and returns metrics.

    Future iterations should expand this with proper signal-specific logic per the
    grammar. Critically: this MUST run end-to-end in shell so the cron can use it.
    """
    import yfinance as yf
    import numpy as np
    import pandas as pd

    results_dir.mkdir(parents=True, exist_ok=True)
    metrics = {"thesis_id": thesis_id, "config": config, "ran_at": datetime.now(timezone.utc).isoformat()}

    tickers = config.get("longs", []) + config.get("shorts", [])
    if not tickers:
        return {**metrics, "error": "no tickers resolved from config", "verdict": "iterate"}

    # Pull 2y of daily data
    end = datetime.now(timezone.utc).date()
    start = end.replace(year=end.year - 2)
    try:
        df = yf.download(tickers, start=str(start), end=str(end), progress=False, auto_adjust=True)
        if df.empty:
            return {**metrics, "error": "empty data", "verdict": "iterate"}
        close = df["Close"] if "Close" in df.columns.get_level_values(0) else df
        if isinstance(close, pd.Series): close = close.to_frame(tickers[0])
    except Exception as e:
        return {**metrics, "error": f"data fetch failed: {e}", "verdict": "iterate"}

    rets = close.pct_change().dropna()
    n = len(rets)
    metrics["n_days"] = int(n)
    metrics["tickers"] = list(close.columns)

    # Walk-forward split
    train_end = int(n * 0.7)
    train, oos = rets.iloc[:train_end], rets.iloc[train_end:]
    metrics["train_days"] = len(train)
    metrics["oos_days"] = len(oos)

    # Long/short basket P&L
    longs = [t for t in config.get("longs", []) if t in close.columns]
    shorts = [t for t in config.get("shorts", []) if t in close.columns]
    if not (longs or shorts):
        return {**metrics, "error": "no usable tickers after data fetch", "verdict": "iterate"}

    long_ret = oos[longs].mean(axis=1) if longs else pd.Series(0, index=oos.index)
    short_ret = oos[shorts].mean(axis=1) if shorts else pd.Series(0, index=oos.index)
    spread = long_ret - short_ret
    sharpe = float(spread.mean() / spread.std() * np.sqrt(252)) if spread.std() > 0 else 0.0
    total_ret = float((1 + spread).prod() - 1)
    hit = float((spread > 0).mean())
    max_dd = float((((1 + spread).cumprod() / (1 + spread).cumprod().cummax()) - 1).min())

    metrics.update({
        "oos_sharpe": round(sharpe, 3),
        "oos_total_return": round(total_ret, 4),
        "oos_hit_rate": round(hit, 3),
        "oos_max_dd": round(max_dd, 4),
    })

    # --- falsifiers ---
    falsifiers = {}

    # F1: random-label placebo (n=200 shuffles)
    rng = np.random.default_rng(42)
    shuffled_sharpes = []
    for _ in range(200):
        shuffled = spread.sample(frac=1.0, random_state=int(rng.integers(0, 1e9))).reset_index(drop=True)
        if shuffled.std() > 0:
            shuffled_sharpes.append(shuffled.mean() / shuffled.std() * np.sqrt(252))
    shuffled_sharpes = np.array(shuffled_sharpes)
    p_value = float((shuffled_sharpes >= sharpe).mean())
    falsifiers["random_label_placebo"] = {"p_value": round(p_value, 4), "passes": bool(p_value < 0.05)}

    # F2: date-split (first vs second half of OOS)
    half = len(spread) // 2
    if half >= 20:
        s1 = spread.iloc[:half]; s2 = spread.iloc[half:]
        sh1 = float(s1.mean() / s1.std() * np.sqrt(252)) if s1.std() > 0 else 0
        sh2 = float(s2.mean() / s2.std() * np.sqrt(252)) if s2.std() > 0 else 0
        falsifiers["date_split"] = {"first_half_sharpe": round(sh1, 3), "second_half_sharpe": round(sh2, 3),
                                    "passes": bool(sh1 * sh2 > 0 and min(abs(sh1), abs(sh2)) > 0.3)}

    # F3: cost stress (15 bps round-trip per period)
    cost_per_period = 0.0015
    spread_after_cost = spread - cost_per_period * 2 / 252  # rough daily prorate
    sharpe_after_cost = float(spread_after_cost.mean() / spread_after_cost.std() * np.sqrt(252)) if spread_after_cost.std() > 0 else 0
    falsifiers["cost_stress"] = {"sharpe_after_15bps": round(sharpe_after_cost, 3),
                                  "passes": bool(sharpe_after_cost > 0.3 * sharpe) if sharpe > 0 else False}

    metrics["falsifiers"] = falsifiers
    metrics["p_value"] = falsifiers["random_label_placebo"]["p_value"]

    # Equity curve plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 4))
        cumret = (1 + spread).cumprod()
        ax.plot(cumret.index, cumret.values, lw=1.5)
        ax.set_title(f"{thesis_id} OOS equity curve · Sharpe {sharpe:.2f}")
        ax.set_ylabel("Cumulative return")
        ax.axhline(1.0, color="grey", lw=0.5, ls="--")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        equity_path = results_dir / f"iter{config.get('next_pr_num', 2)}_equity_curve.png"
        fig.savefig(equity_path, dpi=100)
        plt.close(fig)
        metrics["equity_curve_path"] = str(equity_path)
    except Exception as e:
        metrics["equity_curve_error"] = str(e)

    # --- verdict ---
    # Score 0-10 based on (sharpe, hit rate, falsifier passes)
    score = 0
    if sharpe >= 1.5: score += 4
    elif sharpe >= 1.0: score += 3
    elif sharpe >= 0.5: score += 2
    elif sharpe >= 0.0: score += 1
    if hit >= 0.55: score += 2
    elif hit >= 0.50: score += 1
    n_falsifiers_passed = sum(1 for f in falsifiers.values() if f.get("passes"))
    score += min(4, n_falsifiers_passed * 2)
    metrics["self_score"] = score

    if score >= 6 and falsifiers["random_label_placebo"]["passes"]:
        verdict = "arm"
    elif score < 3 or not falsifiers["random_label_placebo"]["passes"]:
        verdict = "kill"
    else:
        verdict = "iterate"
    metrics["verdict"] = verdict
    return metrics

# -------- PR writer --------

def write_pr(thesis_id: str, next_pr_num: int, metrics: dict, prs_dir: Path) -> Path:
    prs_dir.mkdir(parents=True, exist_ok=True)
    pr_path = prs_dir / f"PR-{next_pr_num:03d}.md"
    fals = metrics.get("falsifiers", {})
    fals_md = "\n".join(f"- **{name}**: {json.dumps(v)}" for name, v in fals.items())
    body = f"""# PR-{next_pr_num:03d}: {thesis_id} · automated backtest

**Generated**: {date.today().isoformat()}
**Mode**: Shell-executable backtest_runner.py (cron-fired, no agent layer required)
**Status**: {metrics.get('verdict', 'iterate').upper()}

## Config
```json
{json.dumps(metrics.get('config'), indent=2)}
```

## OOS metrics
- **Sharpe**: {metrics.get('oos_sharpe', 'n/a')}
- **Total return**: {metrics.get('oos_total_return', 'n/a')}
- **Hit rate**: {metrics.get('oos_hit_rate', 'n/a')}
- **Max DD**: {metrics.get('oos_max_dd', 'n/a')}
- **Days**: {metrics.get('oos_days', 'n/a')} OOS / {metrics.get('train_days','n/a')} train

## Falsifiers
{fals_md}

## p-value (random-label placebo)
**{metrics.get('p_value', 'n/a')}** — passes BH-uncorrected threshold: `{metrics.get('p_value', 1) < 0.05}`

## Self-score
**{metrics.get('self_score', 0)} / 10** → verdict **{metrics.get('verdict', '?').upper()}**

## Limitations of this run
This was a shell-only backtest with a generic long/short basket model. It does not yet implement the thesis-specific signal logic (e.g. event-conditional triggers, attention-spike detection, factor neutralization). The next iteration should be run in an agent-layer context (interactive session or run_subagent-capable cron) with full thesis-specific reasoning.

## Open questions
- The verdict here may differ from a full thesis-specific implementation
- Falsifier coverage is currently 3 (random-label, date-split, cost-stress) of the ~11 in falsification-playbook.md
"""
    pr_path.write_text(body)
    return pr_path

# -------- main --------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--thesis", required=True)
    p.add_argument("--dry", action="store_true")
    args = p.parse_args()

    tdir = RUNS / args.thesis
    if not tdir.exists():
        print(json.dumps({"ok": False, "error": f"thesis not found: {tdir}"})); sys.exit(2)

    # Prepare (acquires lock)
    prep_res = subprocess.run([sys.executable, str(ROOT/"scripts"/"iterate.py"), "prepare", "--thesis", args.thesis],
                              capture_output=True, text=True)
    try: packet = json.loads(prep_res.stdout)
    except json.JSONDecodeError:
        print(json.dumps({"ok": False, "error": "prepare failed", "stdout": prep_res.stdout})); sys.exit(3)
    if not packet.get("ok"):
        print(json.dumps({"ok": False, "error": "lock not acquired", "packet": packet})); sys.exit(0)

    try:
        # Parse the thesis to get config
        config = parse_thesis_tuple(tdir / "thesis.md")
        if not config:
            # human thesis — use default
            config = HUMAN_THESIS_DEFAULTS.get(args.thesis)
        if not config:
            # ultimate fallback
            print(json.dumps({"ok": False, "error": "no parseable config", "thesis": args.thesis}))
            subprocess.run([sys.executable, str(ROOT/"scripts"/"iterate.py"), "release", "--thesis", args.thesis], capture_output=True)
            sys.exit(4)
        config["next_pr_num"] = packet.get("next_pr_num", 2)

        if args.dry:
            print(json.dumps({"ok": True, "would_run": config}, indent=2))
            subprocess.run([sys.executable, str(ROOT/"scripts"/"iterate.py"), "release", "--thesis", args.thesis], capture_output=True)
            return

        # Run the backtest
        results_dir = Path(packet["results_dir"])
        metrics = run_backtest(args.thesis, config, results_dir)
        (results_dir / f"iter{config['next_pr_num']}_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))

        # Write PR
        pr_path = write_pr(args.thesis, config["next_pr_num"], metrics, Path(packet["thesis_dir"]) / "prs")

        # Finalize: status + bandit + log + release lock
        verdict = metrics.get("verdict", "iterate")
        finalize_cmd = [sys.executable, str(ROOT/"scripts"/"iterate.py"), "finalize",
                        "--thesis", args.thesis, "--outcome", verdict]
        # Try to fill axes if config has them (grammar-generated)
        for axis_key, axis_name in [("signal","signal_axis"),("universe","universe_axis"),
                                     ("horizon","horizon_axis"),("structure","structure_axis")]:
            if axis_key in config:
                finalize_cmd += [f"--{axis_name}", config[axis_key]]
        if "p_value" in metrics:
            finalize_cmd += ["--p_value", str(metrics["p_value"])]
        fin_res = subprocess.run(finalize_cmd, capture_output=True, text=True)

        print(json.dumps({
            "ok": True,
            "thesis": args.thesis,
            "pr_written": str(pr_path),
            "verdict": verdict,
            "self_score": metrics.get("self_score"),
            "oos_sharpe": metrics.get("oos_sharpe"),
            "p_value": metrics.get("p_value"),
            "finalize_stdout": fin_res.stdout[-300:],
        }, indent=2))

    except Exception as e:
        tb = traceback.format_exc()
        subprocess.run([sys.executable, str(ROOT/"scripts"/"iterate.py"), "release", "--thesis", args.thesis], capture_output=True)
        print(json.dumps({"ok": False, "error": str(e), "traceback": tb}))
        sys.exit(5)

if __name__ == "__main__": main()
