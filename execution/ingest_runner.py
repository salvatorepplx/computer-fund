"""
Computer Fund — sentiment ingestion runner (Computer-side).

Captures one observed sentiment reading per entity per run and appends it to a
per-entity time-series JSONL. Repeated runs (e.g. via the watch cron, or manual)
accumulate the timestamped SERIES the lead-lag falsifier needs to render a verdict.

This is the thing that converts "one observation" into "a series we can falsify."
Computer-side only (calls live connectors via injected call_tool). Writes observed
events to runs/sentiment/series/<ENTITY>.jsonl and mirrors a price proxy when given.

Usage (Computer-side, with a call_tool that hits the finance connector):
    from execution.ingest_runner import capture
    capture("TICKER:NVDA", call_sentiment=..., call_price=...)
"""
from __future__ import annotations
import json, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERIES_DIR = ROOT / "runs" / "sentiment" / "series"


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def append_observation(entity: str, event: dict, price_proxy: float | None = None) -> str:
    """Append one observed sentiment event (+ optional price proxy) to the entity series."""
    SERIES_DIR.mkdir(parents=True, exist_ok=True)
    path = SERIES_DIR / f"{entity.replace(':', '_')}.jsonl"
    row = {
        "captured_at": _now(),
        "entity": entity,
        "score": event.get("score"),
        "score_raw": event.get("score_raw"),
        "confidence": event.get("confidence"),
        "source": event.get("source"),
        "ts": event.get("ts"),
        "price_proxy": price_proxy,
        "event_id": event.get("event_id"),
    }
    with path.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return str(path.relative_to(ROOT))


def series_length(entity: str) -> int:
    path = SERIES_DIR / f"{entity.replace(':', '_')}.jsonl"
    if not path.exists():
        return 0
    return sum(1 for _ in path.open())


def load_series(entity: str) -> list[dict]:
    """Load a series, skipping any unparseable line defensively.

    A single half-written line (capture append mid-flight, or a concurrent git
    checkout swapping the file) must NOT crash the read or collapse the verdict to
    INSUFFICIENT. We skip bad lines rather than fail the whole load. If a large
    fraction is unparseable, that's a real signal (logged to stderr), not a race.
    """
    path = SERIES_DIR / f"{entity.replace(':', '_')}.jsonl"
    if not path.exists():
        return []
    rows, bad = [], 0
    for l in path.open():
        l = l.strip()
        if not l:
            continue
        try:
            rows.append(json.loads(l))
        except json.JSONDecodeError:
            bad += 1
    if bad:
        import sys as _sys
        print(f"[load_series] skipped {bad} unparseable line(s) in {path.name} "
              f"(likely a mid-write read race; {len(rows)} good rows kept)", file=_sys.stderr)
    return rows


if __name__ == "__main__":
    # self-test: append two synthetic observations and confirm series grows
    import os
    test_entity = "TICKER:_SELFTEST"
    p = SERIES_DIR / f"{test_entity.replace(':','_')}.jsonl"
    if p.exists():
        p.unlink()
    append_observation(test_entity, {"score": 0.1, "confidence": 0.5, "source": "test",
                                     "ts": _now(), "event_id": "x1"}, price_proxy=100.0)
    append_observation(test_entity, {"score": 0.3, "confidence": 0.6, "source": "test",
                                     "ts": _now(), "event_id": "x2"}, price_proxy=101.5)
    print("series length:", series_length(test_entity))
    print("series:", json.dumps(load_series(test_entity), indent=2)[:300])
    p.unlink()  # clean up self-test
    print("self-test ok")
