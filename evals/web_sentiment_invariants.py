"""
Offline invariants for the web-search sentiment scorer (execution/web_sentiment.py).
Pure, deterministic, no connectors. Raises AssertionError on any violation so the
scorer is covered by the regression harness (was previously only a __main__ self-test
-> self-audit scored signal axis tested=False). Run via run_offline_evals.py.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from execution.web_sentiment import normalize


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(f"web_sentiment invariant failed: {msg}")


def run_web_sentiment_invariants() -> dict:
    bull = [
        {"title": "RDDT Strong Buy", "summary": "58% bullish across 3 sources, consensus Strong Buy, 21 buy ratings", "domain": "adanos.org"},
        {"title": "Reddit upgrade", "summary": "analysts raise target, rebound and breakout, constructive", "domain": "marketbeat.com"},
    ]
    bear = [
        {"title": "TSLA probe", "summary": "extremely bearish on Stocktwits, selloff, downgrade, weak momentum, Sell rating", "domain": "stocktwits.com"},
        {"title": "Tesla slides", "summary": "TSLA slides 5.8%, bearish, headwinds, scrutiny, drop below support", "domain": "fxleaders.com"},
    ]

    checks = []
    def chk(name, cond):
        _require(cond, name)
        checks.append(name)

    # 1) directional discrimination
    chk("bull corpus scores positive", normalize(bull).score > 0.2)
    chk("bear corpus scores negative", normalize(bear).score < -0.2)
    # 2) empty corpus is safe (no signal, zero confidence)
    e = normalize([])
    chk("empty corpus -> 0 score, 0 conf", e.score == 0.0 and e.confidence == 0.0)
    # 3) score is bounded [-1, 1]
    chk("score within [-1,1]", -1.0 <= normalize(bull).score <= 1.0 and -1.0 <= normalize(bear).score <= 1.0)
    # 4) EWMA damping: a bull reading after a bearish prior moves up but stays damped below raw
    raw = normalize(bull).score
    damped = normalize(bull, prior_score=-0.5).score
    chk("EWMA damps toward prior", damped < raw and damped > -0.5)
    # 5) confidence rises with more documents
    c1 = normalize(bull[:1]).confidence
    c2 = normalize(bull).confidence
    chk("confidence non-decreasing with more docs", c2 >= c1)
    # 6) explicit readings present are reflected (method tag)
    chk("explicit readings detected", normalize(bull).n_explicit >= 1)

    return {"label": "web_sentiment_invariants", "all_passed": True, "checks": checks, "n": len(checks)}


if __name__ == "__main__":
    import json
    print(json.dumps(run_web_sentiment_invariants(), indent=2))
