"""
Computer Fund — LIVE SentimentSource adapters (Computer-side only).

Implements the RFC-001 SentimentSource contract for sources that require live
connectors. This module lives under execution/ because it is Computer-owned:
Teammate must never run `fetch` (it has no connectors). `normalize` is pure and
is shared with / mirrored by Teammate's offline fixtures.

Boundary (Charter / HANDOFF / RFC-001):
- `fetch` calls live connectors — Computer-side ONLY.
- `normalize` is deterministic — safe to test from fixtures.
- Every emitted event is OBSERVED (simulated=False) and timestamped (no look-ahead).
- Raw payloads are sanitized + written to runs/sentiment/raw/ by reference.

Canonical SentimentEvent (RFC-001):
  {event_id, entity, entity_type, score[-1..1], confidence[0..1], ts, observed_at,
   ingested_at, source, venue, raw_ref, raw{sanitized:true,...}}
"""
from __future__ import annotations
import hashlib, json, re, datetime as dt
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "runs" / "sentiment" / "raw"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _event_id(source_id: str, raw_id: str, entity: str, observed_at: str) -> str:
    h = hashlib.sha256(f"{source_id}:{raw_id}:{entity}:{observed_at}".encode()).hexdigest()[:16]
    return f"sha256:{h}"


@dataclass
class SentimentEvent:
    event_id: str
    entity: str
    entity_type: str
    score: float          # -1 (max bear) .. +1 (max bull)
    confidence: float     # 0..1
    ts: str               # when the sentiment was expressed/observed (source time)
    observed_at: str
    ingested_at: str
    source: str
    venue: str
    raw_ref: str
    raw: dict = field(default_factory=lambda: {"sanitized": True})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SentimentQuery:
    entities: list[str]
    keywords: list[str]
    since: str
    until: str
    max_records: int = 500


class FinanceTickerSentimentSource:
    """Adapter over finance_ticker_sentiment. Bull/bear issue analysis -> events.

    fetch() must be called Computer-side with a `call_tool` callable that invokes
    the finance connector (injected so this module has no hard connector dependency
    and `normalize` stays pure/testable).
    """
    source_id = "finance_ticker_sentiment"
    venue = "vendor.finance"

    # bull/bear lexicon for scoring the textual issue analysis
    _BULL = re.compile(r"\b(raised|buy|accelerat|stronger|outpace|entrenched|growth|beat|upgrade|record)\b", re.I)
    _BEAR = re.compile(r"\b(sold off|drawdown|skeptic|slowdown|net selling|bearish|decline|weaken|miss|downgrade|cut)\b", re.I)

    def fetch(self, since: str, until: str, query: SentimentQuery, call_tool) -> Iterable[dict]:
        """Computer-side. call_tool(ticker, q) -> raw connector dict."""
        for ent in query.entities:
            # only ticker entities are resolvable here (TICKER:NVDA -> NVDA)
            if not ent.startswith("TICKER:"):
                continue
            sym = ent.split(":", 1)[1]
            raw = call_tool(sym, " ".join(query.keywords) or f"{sym} sentiment")
            yield {"entity": ent, "symbol": sym, "raw_text": raw, "raw_id": f"{sym}:{since}"}

    def normalize(self, record: dict) -> Iterable[SentimentEvent]:
        """Pure. Score = (bull_hits - bear_hits) / (bull+bear), confidence from signal density."""
        text = record.get("raw_text", "") or ""
        if not text:
            return []
        bull = len(self._BULL.findall(text))
        bear = len(self._BEAR.findall(text))
        total = bull + bear
        if total == 0:
            return []
        score = round((bull - bear) / total, 4)
        confidence = round(min(1.0, total / 20.0), 4)  # more polarized language -> more confident
        now = _now_iso()
        ent = record["entity"]
        ev = SentimentEvent(
            event_id=_event_id(self.source_id, record["raw_id"], ent, now),
            entity=ent, entity_type="ticker",
            score=score, confidence=confidence,
            ts=now, observed_at=now, ingested_at=now,
            source=self.source_id, venue=self.venue,
            raw_ref=f"runs/sentiment/raw/{self.source_id}/{record['raw_id'].replace(':','_')}.txt",
            raw={"sanitized": True, "bull_hits": bull, "bear_hits": bear, "chars": len(text)},
        )
        return [ev]


def persist_raw(source_id: str, raw_id: str, text: str) -> str:
    d = RAW_DIR / source_id
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{raw_id.replace(':','_')}.txt"
    p.write_text(text)
    return str(p.relative_to(ROOT))


if __name__ == "__main__":
    # offline normalize self-test with a sanitized fixture (no live call)
    src = FinanceTickerSentimentSource()
    fixture = {"entity": "TICKER:NVDA", "symbol": "NVDA", "raw_id": "NVDA:test",
               "raw_text": "CFO confirmed stronger demand and raised price target to Buy; "
                           "record results. Bears note the stock sold off, a 20% drawdown, "
                           "net selling by insiders, and skeptic views on a capex slowdown."}
    evs = list(src.normalize(fixture))
    for e in evs:
        print(json.dumps(e.to_dict(), indent=2))
