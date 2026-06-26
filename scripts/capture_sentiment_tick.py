"""
One-shot sentiment+price capture for a watched entity. Designed to be called from
the watch cron each tick so the timestamped series accumulates automatically toward
the lead-lag falsifier's minimum-N. Computer-side (uses live connectors via external-tool CLI).

Appends one observed point to runs/sentiment/series/<ENTITY>.jsonl. Idempotency is loose:
it captures whatever the live tools return now; duplicate-ish points are fine for a
time series (lead-lag dedupes by timestamp spacing downstream).

Sentiment capture is bounded-retry hardened for transient source rate limits: the
finance sentiment call is attempted at most 3 times, with capped backoff of 15s
then 45s between failed attempts. Empty payloads or payloads that normalize to no
sentiment signal are retried, but no series row is appended until a valid event is
normalized. If every attempt fails, the script still fails gracefully with
captured:false so the cron can surface the missed tick without duplicating data.

Usage: python scripts/capture_sentiment_tick.py TICKER:NVDA NVDA
"""
from __future__ import annotations
import sys, json, subprocess, re, datetime as dt, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from execution.sentiment_adapters import FinanceTickerSentimentSource, persist_raw
from execution.ingest_runner import append_observation, series_length, load_series

SENTIMENT_CAPTURE_MAX_ATTEMPTS = 3
SENTIMENT_CAPTURE_BACKOFF_SECONDS = (15.0, 45.0)


def call_tool(source_id: str, tool_name: str, arguments: dict) -> dict:
    payload = json.dumps({"source_id": source_id, "tool_name": tool_name, "arguments": arguments})
    out = subprocess.run(["external-tool", "call", payload], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(out.stderr[:300])
    return json.loads(out.stdout)


def capture_sentiment_with_retry(
    entity: str,
    symbol: str,
    *,
    prior_score: float | None = None,
    call_tool_fn=None,
    sleep_fn=None,
    max_attempts: int = SENTIMENT_CAPTURE_MAX_ATTEMPTS,
    backoff_seconds: tuple[float, ...] = SENTIMENT_CAPTURE_BACKOFF_SECONDS,
) -> dict:
    """Return the first normalizable sentiment event, retrying transient no-signal responses.

    This helper is deterministic under injected `call_tool_fn`/`sleep_fn` and does not append
    to the observed series. It persists raw text only for the successful normalized attempt.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    call_tool_fn = call_tool if call_tool_fn is None else call_tool_fn
    sleep_fn = time.sleep if sleep_fn is None else sleep_fn
    src = FinanceTickerSentimentSource()
    failures: list[dict] = []
    for attempt in range(1, max_attempts + 1):
        raw_text = ""
        try:
            rid = f"{symbol}:{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H%M')}:attempt{attempt}"
            record = src.fetch_record(entity, symbol, rid, call_tool_fn)
            raw_text = record["raw_text"]
            if raw_text.strip():
                record["prior_score"] = prior_score
                events = list(src.normalize(record))
                if events:
                    persist_raw("finance_ticker_sentiment", rid, raw_text)
                    return {
                        "captured": True,
                        "event": events[0].to_dict(),
                        "attempts": attempt,
                    }
                reason = "no sentiment signal in text"
            else:
                reason = "empty sentiment response"
        except Exception as exc:
            reason = f"sentiment call failed: {str(exc)[:120]}"

        failures.append({"attempt": attempt, "reason": reason, "raw_chars": len(raw_text)})
        if attempt < max_attempts and backoff_seconds:
            sleep_fn(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])

    return {
        "captured": False,
        "reason": failures[-1]["reason"] if failures else "sentiment capture failed",
        "attempts": max_attempts,
        "failures": failures,
    }


def capture(entity: str, symbol: str) -> dict:
    # EWMA smoothing: feed the last observed score as prior to damp single-fetch noise.
    prior = None
    series = load_series(entity)
    if series:
        prior = series[-1].get("score")
    sentiment = capture_sentiment_with_retry(entity, symbol, prior_score=prior)
    if not sentiment["captured"]:
        return sentiment
    ev = sentiment["event"]

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
            "series_path": ref, "series_length": series_length(entity),
            "sentiment_attempts": sentiment["attempts"]}


if __name__ == "__main__":
    entity = sys.argv[1] if len(sys.argv) > 1 else "TICKER:NVDA"
    symbol = sys.argv[2] if len(sys.argv) > 2 else "NVDA"
    print(json.dumps(capture(entity, symbol), indent=2))
