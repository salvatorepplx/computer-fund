"""
Computer Fund — Strategy hypothesis space + generator.

Fixes the core gap: we were testing ONE thesis (sentiment lead-lag, 4 single names)
when the mandate is a BROAD hypothesis space. A thesis is a tuple from the autoresearch
grammar; this module enumerates the space and samples diverse, independent, falsifiable
theses so the fund is a PORTFOLIO of bets, not a single fragile guess.

THESIS := (SIGNAL, UNIVERSE, HORIZON, STRUCTURE, RISK)

Each generated thesis gets a stable id and a registry entry in runs/strategies/REGISTRY.json
with status=proposed. The falsification pipeline (lead-lag / null / circularity, and future
backtest harnesses) advances each independently: proposed -> testing -> {edge | killed}.

This module is PURE generation + registry bookkeeping. It places NOTHING and fetches
no live data. Signals that need a data source declare it so the runner knows what to wire.
"""
from __future__ import annotations
import json, hashlib, itertools, random, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "runs" / "strategies" / "REGISTRY.json"

# ---- the grammar dimensions (a deliberately broad, tractable subset) ----------
SIGNALS = [
    # (name, data_source, short_desc)
    ("sentiment_leadlag", "web_search", "projected sentiment leads price (the seed thesis)"),
    ("sentiment_reversal", "web_search", "sentiment extreme -> mean-reversion fade"),
    ("mention_velocity", "web_search", "acceleration of mention/coverage volume predicts move"),
    ("analyst_revision_breadth", "web_search", "breadth of target/rating changes predicts drift (PEAD-like)"),
    ("price_momentum", "price_only", "trailing return continuation (12-1 / 5d)"),
    ("short_interest_squeeze", "web_search", "high+rising short interest -> squeeze asymmetry"),
    ("vol_regime_gate", "price_only", "realized-vol regime gates a momentum/reversion overlay"),
    ("cross_source_divergence", "web_search", "Reddit vs News sentiment gap predicts reconciliation"),
]
# UNIVERSE is OPEN: anything tradeable on Robinhood Agentic (all US equities + ETFs,
# options L2, crypto watch-only). We do NOT hardcode a basket. A universe spec is a
# SELECTOR + a discovery method that resolves to concrete tickers at test time via RH
# scanners (DAILY_GAINERS/LOSERS, RSI, volume, 52w) and web research. The members list
# is a seed/example only; the runner re-resolves the live constituents each test.
UNIVERSES = [
    ("rh_all_liquid", "selector:liquid_us_equities_etfs", "any liquid RH equity/ETF (scanner-resolved)"),
    ("rh_scanner_movers", "selector:rh_scanner(DAILY_GAINERS,DAILY_LOSERS,top_volume)", "today's movers from RH scanners"),
    ("rh_high_short", "selector:research(highest_short_interest)", "research-resolved high-short cohort"),
    ("rh_thematic", "selector:research(thematic_basket:<theme>)", "research-resolved theme basket (AI/memory/power/GLP-1/...)"),
    ("rh_sector_etfs", "selector:fixed(XLK,XLF,XLE,XLU,XLV,XLY,XLI,XLB,XLP,XLRE,XLC)", "all sector ETFs"),
    ("rh_index_etfs", "selector:fixed(SPY,QQQ,IWM,MDY)", "broad index ETFs"),
    ("rh_crypto_proxies", "selector:fixed(COIN,MSTR,MARA,RIOT)", "crypto-beta equities (crypto itself watch-only)"),
    ("battle_singles_seed", "selector:fixed(NVDA,RDDT,TSLA,SNDK)", "current contested singles (seed, not a cage)"),
]
HORIZONS = ["intraday", "1d", "3d", "5d", "1w"]
STRUCTURES = ["long_flat", "long_short_single", "ranked_decile", "pair_neutral", "regime_overlay"]
RISKS = ["equal_weight", "vol_target", "kelly_capped"]


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def thesis_id(sig, uni, hor, struct, risk):
    raw = f"{sig}|{uni}|{hor}|{struct}|{risk}"
    return "TH-" + hashlib.sha256(raw.encode()).hexdigest()[:10]


def _capabilities_for(sig_row) -> list[str]:
    """Which of Computer's OWN capabilities research+test this signal.
    This is the point: lean on subagents/web-research/finance-tools/scanners,
    not hand-coded heuristics."""
    sig, datasrc, _ = sig_row
    caps = ["leadlag_real+permutation (verdict harness)"]
    if datasrc == "web_search":
        caps += ["pplx_sdk.search.web (qualitative signal)",
                 "research subagent (deep multi-source falsification)",
                 "wide_browse (cross-sectional coverage at scale)"]
    if datasrc == "price_only":
        caps += ["finance connector / RH scanners (price/vol/technicals)"]
    if sig in ("short_interest_squeeze", "analyst_revision_breadth", "cross_source_divergence"):
        caps += ["research subagent (structured data extraction)"]
    caps += ["parallel subagents (test many universe members at once)"]
    return caps


def make_thesis(sig_row, uni_row, hor, struct, risk):
    sig, datasrc, sdesc = sig_row
    uni, selector, udesc = uni_row
    tid = thesis_id(sig, uni, hor, struct, risk)
    return {
        "id": tid,
        "signal": sig, "data_source": datasrc, "signal_desc": sdesc,
        "universe": uni, "selector": selector, "universe_desc": udesc,
        "horizon": hor, "structure": struct, "risk": risk,
        "status": "proposed",
        "falsifiers_required": ["min_n", "permutation_null", "circularity_guard",
                                 "cross_sectional_generalization"],
        "capabilities": _capabilities_for(sig_row),
        "created_at": _now(),
        "notes": f"{sig} on {uni} @ {hor}, {struct}/{risk}",
    }


def load_registry() -> dict:
    if REG.exists():
        try:
            return json.loads(REG.read_text())
        except Exception:
            pass
    return {"_doc": "Computer Fund strategy portfolio. Each entry is an independent, "
                    "falsifiable thesis from the grammar. The fund is a PORTFOLIO of bets.",
            "updated": _now(), "theses": {}}


def save_registry(reg: dict):
    REG.parent.mkdir(parents=True, exist_ok=True)
    reg["updated"] = _now()
    REG.write_text(json.dumps(reg, indent=2))


def total_space_size() -> int:
    return len(SIGNALS) * len(UNIVERSES) * len(HORIZONS) * len(STRUCTURES) * len(RISKS)


def sample(n: int, seed: int | None = None, novelty_bias: bool = True) -> list[dict]:
    """Sample n diverse theses not already in the registry (explore breadth first)."""
    rng = random.Random(seed)
    reg = load_registry()
    existing = set(reg["theses"].keys())
    out, tries = [], 0
    # bias exploration: don't over-sample the seed signal we already know is weak
    sig_pool = SIGNALS[:]
    while len(out) < n and tries < n * 50:
        tries += 1
        sig = rng.choice(sig_pool)
        uni = rng.choice(UNIVERSES)
        hor = rng.choice(HORIZONS)
        struct = rng.choice(STRUCTURES)
        risk = rng.choice(RISKS)
        t = make_thesis(sig, uni, hor, struct, risk)
        if t["id"] in existing or any(o["id"] == t["id"] for o in out):
            continue
        out.append(t)
    return out


def register(theses: list[dict]) -> dict:
    reg = load_registry()
    for t in theses:
        reg["theses"][t["id"]] = t
    save_registry(reg)
    return reg


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--dry", action="store_true", help="print only, do not register")
    a = ap.parse_args()
    print(f"hypothesis space size: {total_space_size()} tuples "
          f"({len(SIGNALS)} signals x {len(UNIVERSES)} universes x {len(HORIZONS)} horizons "
          f"x {len(STRUCTURES)} structures x {len(RISKS)} risk models)")
    theses = sample(a.n, seed=a.seed)
    for t in theses:
        print(f"  {t['id']}  {t['signal']:24s} {t['universe']:18s} {t['horizon']:8s} {t['structure']:18s} {t['risk']}")
    if not a.dry:
        reg = register(theses)
        print(f"registered {len(theses)} new theses; portfolio now holds {len(reg['theses'])}")
