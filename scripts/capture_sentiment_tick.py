"""
One-shot sentiment+price capture for a watched entity. Designed to be called from
the watch cron each tick so the timestamped series accumulates automatically toward
the lead-lag falsifier's minimum-N. Computer-side (uses live connectors via external-tool CLI).

Appends one observed point to runs/sentiment/series/<ENTITY>.jsonl. Idempotency is loose:
it captures whatever the live tools return now; duplicate-ish points are fine for a
time series (lead-lag dedupes by timestamp spacing downstream).

Usage: python scripts/capture_sentiment_tick.py TICKER:NVDA NVDA
"""
from __future__ import annotations
import sys, json, subprocess, re, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from execution.sentiment_adapters import FinanceTickerSentimentSource, persist_raw
from execution.ingest_runner import append_observation, series_length, load_series


def call_tool(source_id: str, tool_name: str, arguments: dict) -> dict:
    payload = json.dumps({"source_id": source_id, "tool_name": tool_name, "arguments": arguments})
    out = subprocess.run(["external-tool", "call", payload], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(out.stderr[:300])
    return json.loads(out.stdout)


def capture(entity: str, symbol: str) -> dict:
    # 1) live sentiment
    sent = call_tool("finance", "finance_ticker_sentiment",
                     {"ticker_symbol": symbol, "query": f"{symbol} bull vs bear",
                      "action": f"Analyzing bulls vs bears for {symbol}"})
    raw_text = sent.get("content", "") if isinstance(sent, dict) else str(sent)
    rid = f"{symbol}:{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H%M')}"
    persist_raw("finance_ticker_sentiment", rid, raw_text)
    src = FinanceTickerSentimentSource()
    # EWMA smoothing: feed the last observed score as prior to damp single-fetch noise.
    prior = None
    series = load_series(entity)
    if series:
        prior = series[-1].get("score")
    events = list(src.normalize({"entity": entity, "symbol": symbol, "raw_id": rid,
                                 "raw_text": raw_text, "prior_score": prior}))
    if not events:
        return {"captured": False, "reason": "no sentiment signal in text"}
    ev = events[0].to_dict()

    # 2) live price proxy
    price = None
    try:
        q = call_tool("robinhood", "get_equity_quotes", {"symbols": [symbol]})
        res = q["data"]["results"][0]["quote"]
        price = float(res.get("last_non_reg_trade_price") or res.get("last_trade_price"))
    except Exception as e:
        print(f"[warn] price proxy unavailable: {str(e)[:100]}")

    ref = append_observation(entity, ev, price_proxy=price)
    return {"captured": True, "entity": entity, "score": ev["score"],
            "confidence": ev["confidence"], "price_proxy": price,
            "series_path": ref, "series_length": series_length(entity)}


if __name__ == "__main__":
    entity = sys.argv[1] if len(sys.argv) > 1 else "TICKER:NVDA"
    symbol = sys.argv[2] if len(sys.argv) > 2 else "NVDA"
    print(json.dumps(capture(entity, symbol), indent=2))
