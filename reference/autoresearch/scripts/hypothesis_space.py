"""Hypothesis grammar + sampler with coherence rules.

A THESIS is (signal, universe, horizon, structure). The sampler maintains a
Beta(α,β) prior over each arm and draws via Thompson sampling — surviving
hypotheses tighten the prior toward exploit, failing ones nudge back toward explore.

Coherence rules reject samples that have no plausible causal mechanism
(e.g. yield_curve_slope on crypto) so the iterator doesn't waste cycles on noise.

Usage:
    python hypothesis_space.py sample
    python hypothesis_space.py sample --n 20
    python hypothesis_space.py status
    python hypothesis_space.py update --axis signal --value price_momentum --outcome win
"""
from __future__ import annotations
import argparse, json, random, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
EVALS = ROOT / "evals"
EVALS.mkdir(exist_ok=True)
REGISTRY = json.loads((DATA / "registry.json").read_text())
ARMS_PATH = EVALS / "bandit_arms.json"

# Import signal status so we only sample implemented signals.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from signal_library import signal_status_report
    _SIG_STATUS = signal_status_report()
except Exception as _e:
    print(f"# warn: signal_library import failed: {_e}", file=sys.stderr)
    _SIG_STATUS = {}

# Coherence: (signal -> compatible universe whitelist). Empty list = all OK.
SIGNAL_UNIVERSE_AFFINITY = {
    "yield_curve_slope":          ["spy_indexed", "sector_etfs", "rates", "factor_etfs", "agi_buildout_full"],
    "real_yields":                ["commodities", "spy_indexed", "rates", "factor_etfs", "agi_buildout_full"],
    "epu_index":                  ["spy_indexed", "sector_etfs", "factor_etfs"],
    "credit_spreads_ighy":        ["spy_indexed", "sector_etfs", "rates", "factor_etfs"],
    "financial_conditions_index": ["spy_indexed", "sector_etfs", "rates", "factor_etfs"],
    "vix_term_structure":         ["spy_indexed", "sector_etfs", "factor_etfs"],
    "price_momentum":             ["spy_indexed", "sector_etfs", "factor_etfs", "agi_buildout_full", "social_attention_basket", "retail_attention_basket"],
    "realized_vol":               ["spy_indexed", "sector_etfs", "factor_etfs", "agi_buildout_full"],
    "volume_zscore":              ["social_attention_basket", "retail_attention_basket", "agi_buildout_full"],
    "pct_above_200dma":           ["spy_indexed", "sector_etfs", "factor_etfs", "agi_buildout_full"],
}

INCOHERENT_TUPLES = {
    ("intraday_oc", "pair_beta_neutral"),
    ("intraday_oc", "ranked_decile"),
    ("event_t_minus_5_to_plus_5", "long_only"),
}

US_MACRO_SIGNALS = {"yield_curve_slope","epu_index","credit_spreads_ighy","real_yields","financial_conditions_index","vix_term_structure"}

def _is_coherent(signal, universe, horizon, structure):
    affinity = SIGNAL_UNIVERSE_AFFINITY.get(signal)
    if affinity is not None and universe not in affinity: return False
    if (horizon, structure) in INCOHERENT_TUPLES: return False
    if universe == "crypto" and signal in US_MACRO_SIGNALS: return False
    return True

def _load_arms():
    if ARMS_PATH.exists(): return json.loads(ARMS_PATH.read_text())
    return {"arms": {}, "updated_at": None}

def _signal_keys():
    """Only signals with real implementations."""
    implemented = [k for k, v in _SIG_STATUS.items() if v == "ok"]
    if implemented: return implemented
    # fallback if signal_library failed to load
    return [k for k, v in REGISTRY["signals"].items() if v.get("status") not in ("PLANNED","WIP")]

def _universe_keys():
    return list(REGISTRY["universes"].keys())

def thompson_sample(arms_state):
    sigs = _signal_keys(); unis = _universe_keys()
    hors = REGISTRY["horizons"]; structs = REGISTRY["structures"]

    def draw_axis(axis_name, options):
        scores = {}
        for opt in options:
            c = arms_state["arms"].get(f"{axis_name}::{opt}", {"a":1,"b":1})
            scores[opt] = random.betavariate(c["a"], c["b"])
        return max(scores, key=scores.get)

    s = u = h = st = None
    for _ in range(50):
        s = draw_axis("signal", sigs)
        u = draw_axis("universe", unis)
        h = draw_axis("horizon", hors)
        st = draw_axis("structure", structs)
        if _is_coherent(s, u, h, st): break

    return {"signal": s, "universe": u, "horizon": h, "structure": st,
            "thesis_id": f"H_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{random.randint(1000,9999)}",
            "sampled_at": datetime.now(timezone.utc).isoformat()}

def update_arm(arms_state, axis, value, outcome):
    key = f"{axis}::{value}"
    arm = arms_state["arms"].setdefault(key, {"a":1,"b":1})
    if outcome == "win": arm["a"] += 1
    elif outcome == "loss": arm["b"] += 1
    arms_state["updated_at"] = datetime.now(timezone.utc).isoformat()

def sample(n=1):
    state = _load_arms()
    out = [thompson_sample(state) for _ in range(n)]
    ARMS_PATH.write_text(json.dumps(state, indent=2))
    return out

def update(axis, value, outcome):
    state = _load_arms()
    update_arm(state, axis, value, outcome)
    ARMS_PATH.write_text(json.dumps(state, indent=2))
    return state

def status():
    state = _load_arms()
    out = {"axes": {}, "updated_at": state.get("updated_at"),
           "implemented_signals": [k for k,v in _SIG_STATUS.items() if v=="ok"]}
    for k, arm in state["arms"].items():
        axis, val = k.split("::", 1)
        out["axes"].setdefault(axis, []).append({"value": val, "wins": arm["a"]-1, "losses": arm["b"]-1,
                                                  "posterior_mean": arm["a"]/(arm["a"]+arm["b"])})
    for axis in out["axes"]:
        out["axes"][axis].sort(key=lambda r: -r["posterior_mean"])
    return out

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample"); s.add_argument("--n", type=int, default=1)
    u = sub.add_parser("update"); u.add_argument("--axis", required=True); u.add_argument("--value", required=True); u.add_argument("--outcome", required=True)
    sub.add_parser("status")
    a = p.parse_args()
    if a.cmd == "sample": print(json.dumps(sample(a.n), indent=2))
    elif a.cmd == "update": print(json.dumps(update(a.axis, a.value, a.outcome), indent=2))
    elif a.cmd == "status": print(json.dumps(status(), indent=2))

if __name__ == "__main__": main()
