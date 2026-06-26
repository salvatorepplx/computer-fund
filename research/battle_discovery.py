"""
Computer Fund — Battle-location discovery.

A "battle location" is a contested arena where bull/bear views collide and sentiment is being
repriced — the only places alpha-from-sentiment lives. This module turns raw market state into
candidate battles and writes them into the knowledge graph.

This file is the PURE logic (ranking, candidate construction). The live data (scanner results,
quotes, earnings, ticker sentiment) is fetched by the agent via the Robinhood + finance connectors
and passed in as plain dicts — keeping this testable offline and honest about provenance.

Inputs the agent should gather each discovery tick (all timestamped):
  movers      — [{symbol, pct_change, volume}]  from RH scanners (DAILY_GAINERS/LOSERS, RSI, vol)
  earnings    — [{symbol, report_date, when}]   from RH get_earnings_calendar (next ~7d)
  sentiment   — {symbol: {score, confidence}}   from finance_ticker_sentiment (observed)
  fundamentals- {symbol: {pe, short_interest?}} optional context

A battle is "hot" when there's: a move (price dislocation) + a catalyst (dated event) +
sentiment that is either extreme or rapidly changing (the crowd is mid-reprice).
"""
from __future__ import annotations


CONTESTED_KEYWORDS = [
    "ai", "capex", "bubble", "squeeze", "short", "guidance", "miss", "beat",
    "margin", "demand", "regulation", "antitrust", "recall", "lawsuit",
]


def score_battle(symbol: str, mover: dict | None, has_catalyst: bool,
                 sentiment: dict | None) -> dict:
    """
    Heuristic contestedness score. Higher = more worth researching.
    Components (each 0..1):
      dislocation  — abs % move, capped
      catalyst     — 1 if a dated event is imminent
      sent_extreme — how far observed sentiment is from neutral
      sent_uncert  — low confidence = more contested = more opportunity to predate
    """
    pct = abs((mover or {}).get("pct_change", 0.0)) / 10.0  # 10% move -> 1.0
    dislocation = min(1.0, pct)
    catalyst = 1.0 if has_catalyst else 0.0
    s = sentiment or {}
    sent_extreme = min(1.0, abs(s.get("score", 0.0)))
    sent_uncert = 1.0 - min(1.0, s.get("confidence", 0.5))
    score = (0.35 * dislocation + 0.30 * catalyst +
             0.20 * sent_extreme + 0.15 * sent_uncert)
    return {
        "symbol": symbol,
        "score": round(score, 4),
        "components": {
            "dislocation": round(dislocation, 3),
            "catalyst": catalyst,
            "sent_extreme": round(sent_extreme, 3),
            "sent_uncert": round(sent_uncert, 3),
        },
    }


def discover_battles(movers: list[dict], earnings: list[dict],
                     sentiment: dict, top_k: int = 5) -> list[dict]:
    """Combine signals into ranked battle candidates."""
    earn_symbols = {e["symbol"] for e in earnings}
    by_symbol = {m["symbol"]: m for m in movers}
    universe = set(by_symbol) | earn_symbols | set(sentiment)
    scored = []
    for sym in universe:
        b = score_battle(sym, by_symbol.get(sym), sym in earn_symbols, sentiment.get(sym))
        # seed a direction hint from observed sentiment + move
        sent_score = sentiment.get(sym, {}).get("score", 0.0)
        move = by_symbol.get(sym, {}).get("pct_change", 0.0)
        b["seed_direction"] = 1.0 if (sent_score + move / 100.0) >= 0 else -1.0
        scored.append(b)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


if __name__ == "__main__":
    movers = [
        {"symbol": "NVDA", "pct_change": -4.2, "volume": 5e8},
        {"symbol": "RDDT", "pct_change": 9.1, "volume": 3e7},
        {"symbol": "SMCI", "pct_change": 12.5, "volume": 4e7},
    ]
    earnings = [{"symbol": "NVDA", "report_date": "2026-08-27", "when": "pm"}]
    sentiment = {
        "NVDA": {"score": -0.3, "confidence": 0.4},
        "RDDT": {"score": 0.6, "confidence": 0.55},
        "SMCI": {"score": 0.1, "confidence": 0.2},
    }
    import json
    print(json.dumps(discover_battles(movers, earnings, sentiment), indent=2))
