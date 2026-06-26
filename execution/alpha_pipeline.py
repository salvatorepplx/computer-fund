"""
Computer Fund — Alpha pipeline: verdict -> ranked conviction -> PROPOSED artifact.

Turns a *surviving* lead-lag signal into a ranked, schema-conformant proposal
(runs/PROPOSED/<id>.json, cf.integration.v1) ready for Computer to promote under
the Charter rails. This is the bridge between "the signal survived falsification"
and "a trade gets placed" — built NOW so there is ZERO lag between an authoritative
EDGE verdict and an actionable proposal.

HARD boundaries (Charter / HANDOFF):
- This module is PROPOSE-ONLY. It writes runs/PROPOSED/ artifacts that are
  incapable of placing or implying an order: no order fields, no sizing, no
  broker/account data, no execution wording. Promotion (PROPOSED->ARMED->...)
  and all sizing/review/placement happen ELSEWHERE under execution/safety.py.
- A name is eligible ONLY if its verdict is authoritative EDGE and NOT circular.
  PRELIMINARY / KILL / circular-flagged names are rejected (logged as such).
- conviction is a RANKING signal, not a position size. Sizing is decided at
  promotion time by safety.check_sizing against the live account + risk phase.

Conviction score (0..1), purely from the validated signal + sentiment state:
    0.45 * lead_strength   (best_corr at the leading lag, clamped)
    0.25 * lead_cleanliness(positive lag dominance vs coincident/lagging)
    0.20 * sentiment_conviction (|current sentiment| * confidence)
    0.10 * corroboration   (n_spaced depth past the authoritative floor)
Circularity or non-EDGE => conviction forced to 0 and name rejected.
"""
from __future__ import annotations
import sys, json, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from evals.leadlag_real import probe
from execution.ingest_runner import load_series

PROPOSED_DIR = ROOT / "runs" / "PROPOSED"


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def conviction_from_verdict(v: dict, sent_state: dict) -> dict:
    """Compute a 0..1 conviction RANKING score from a verdict + sentiment state.
    Returns {conviction, eligible, reason, components}."""
    verdict = v.get("verdict", "")
    circular = v.get("circularity_flag", False)
    authoritative = v.get("authoritative", False)

    # Eligibility: only an authoritative, non-circular EDGE can be traded.
    if circular:
        return {"conviction": 0.0, "eligible": False,
                "reason": f"circularity_flag (contemp_corr={v.get('contemp_corr')})",
                "components": {}}
    if not authoritative or verdict != "EDGE":
        return {"conviction": 0.0, "eligible": False,
                "reason": f"verdict={verdict} authoritative={authoritative} (need authoritative EDGE)",
                "components": {}}

    best_corr = abs(v.get("best_corr", 0.0))
    best_lag = v.get("best_lag", 0)
    all_lags = v.get("all_lags", [])
    n = v.get("n", 0)
    min_n = v.get("min_n", 24)

    lead_strength = _clip(best_corr)
    # cleanliness: how much the leading lags dominate coincident/lagging corr
    pos = [abs(r["corr"]) for r in all_lags if r["lag"] >= 1]
    nonpos = [abs(r["corr"]) for r in all_lags if r["lag"] <= 0]
    if pos and nonpos:
        cleanliness = _clip((max(pos) - max(nonpos)) + 0.5)  # center ~0.5
    else:
        cleanliness = 0.5
    sval = abs(sent_state.get("score", 0.0)) * sent_state.get("confidence", 0.0)
    sentiment_conv = _clip(sval)
    corroboration = _clip((n - min_n) / float(min_n)) if n >= min_n else 0.0

    conviction = _clip(
        0.45 * lead_strength + 0.25 * cleanliness +
        0.20 * sentiment_conv + 0.10 * corroboration)

    return {"conviction": round(conviction, 4), "eligible": True,
            "reason": f"authoritative EDGE at lag={best_lag}",
            "components": {"lead_strength": round(lead_strength, 4),
                           "cleanliness": round(cleanliness, 4),
                           "sentiment_conv": round(sentiment_conv, 4),
                           "corroboration": round(corroboration, 4)}}


def _sentiment_state(entity: str) -> dict:
    s = load_series(entity)
    if not s:
        return {"score": 0.0, "confidence": 0.0}
    last = s[-1]
    sc = last.get("score_raw")
    if sc is None:
        sc = last.get("score", 0.0)
    return {"score": sc or 0.0, "confidence": last.get("confidence", 0.0),
            "price_proxy": last.get("price_proxy")}


def rank(entities: list[str], min_n: int = 24) -> list[dict]:
    """Rank entities by conviction. Returns sorted list of dicts (highest first)."""
    out = []
    for e in entities:
        v = probe(e, min_n=min_n)
        ss = _sentiment_state(e)
        c = conviction_from_verdict(v, ss)
        out.append({"entity": e, "verdict": v.get("verdict"),
                    "authoritative": v.get("authoritative"),
                    "best_lag": v.get("best_lag"), "best_corr": v.get("best_corr"),
                    "circular": v.get("circularity_flag"),
                    "sentiment": ss, **c})
    out.sort(key=lambda r: r["conviction"], reverse=True)
    return out


def write_proposed(entity: str, conviction_row: dict) -> str:
    """Write a schema-conformant PROPOSE-ONLY artifact. NO order/sizing/exec fields."""
    if not conviction_row.get("eligible"):
        raise ValueError(f"refusing to propose ineligible entity {entity}: {conviction_row.get('reason')}")
    PROPOSED_DIR.mkdir(parents=True, exist_ok=True)
    sym = entity.split(":")[-1]
    date = dt.date.today().isoformat()
    aid = f"battle-{sym}-leadlag-{date}"
    art = {
        "schema_version": "cf.integration.v1",
        "artifact_id": aid,
        "artifact_type": "proposal",
        "state": "PROPOSED",
        "created_at": _now(),
        "writer": "computer",           # Computer-generated from its own validated signal
        "owner": "computer",
        "simulated": False,
        "payload": {
            "thesis": f"predate sentiment->price lead-lag edge on {sym} "
                      f"(authoritative EDGE, conviction={conviction_row['conviction']})",
            "entities": [entity],
            "conviction": conviction_row["conviction"],
            "conviction_components": conviction_row["components"],
            "signal_provenance": {
                "verdict": conviction_row.get("verdict"),
                "best_lag": conviction_row.get("best_lag"),
                "best_corr": conviction_row.get("best_corr"),
                "circular": conviction_row.get("circular"),
                "source": "evals/leadlag_real.py on web_search_sentiment series",
            },
            "dossier_refs": [f"research/discoveries/"],
            "requested_live_checks": ["quote_snapshot", "account_safety_review",
                                       "sentiment_capture_refresh", "kill_switch_status"],
            "non_authorizations": ["no_order", "no_sizing", "no_execution_instruction"],
            "open_risks": ["Computer must verify live price, account, sizing caps, "
                           "kill-switch, and re-confirm the edge has not decayed before promoting."],
        },
    }
    path = PROPOSED_DIR / f"{aid}.json"
    path.write_text(json.dumps(art, indent=2))
    return str(path.relative_to(ROOT))


if __name__ == "__main__":
    ents = sys.argv[1:] or ["TICKER:NVDA", "TICKER:RDDT", "TICKER:TSLA", "TICKER:SNDK"]
    ranked = rank(ents)
    print(json.dumps(ranked, indent=2))
    eligible = [r for r in ranked if r["eligible"]]
    print(f"\n{len(eligible)} eligible (authoritative non-circular EDGE) of {len(ents)}")
    for r in eligible:
        p = write_proposed(r["entity"], r)
        print(f"  wrote {p} (conviction={r['conviction']})")
