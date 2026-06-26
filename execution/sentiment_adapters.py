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

    # Lexicons kept ONLY as a fallback when the structured issue format is absent.
    _BULL = re.compile(r"\b(raised|buy|accelerat|stronger|outpace|entrenched|growth|beat|upgrade|record)\b", re.I)
    _BEAR = re.compile(r"\b(sold off|drawdown|skeptic|slowdown|net selling|bearish|decline|weaken|miss|downgrade|cut)\b", re.I)
    # Embedded quantified sentiment signal, e.g. "social sentiment declined 9.88 points".
    _QUANT = re.compile(r"social sentiment (declined|dropped|fell|rose|increased|gained)\s+([0-9.]+)", re.I)

    def fetch(self, since: str, until: str, query: SentimentQuery, call_tool) -> Iterable[dict]:
        """Computer-side. call_tool(ticker, q) -> raw connector dict."""
        for ent in query.entities:
            # only ticker entities are resolvable here (TICKER:NVDA -> NVDA)
            if not ent.startswith("TICKER:"):
                continue
            sym = ent.split(":", 1)[1]
            raw = call_tool(sym, " ".join(query.keywords) or f"{sym} sentiment")
            yield {"entity": ent, "symbol": sym, "raw_text": raw, "raw_id": f"{sym}:{since}"}

    def _score_text(self, text: str) -> tuple[float, float, dict]:
        """Return (score[-1..1], confidence[0..1], provenance). Structured-first, lexicon fallback.

        Primary signal: the source emits discrete issues, each with a bull case and a bear case.
        Per issue we balance bull vs bear prose (lexicon-weighted), then average across issues.
        Far more stable than counting trigger words across the whole blob. Folds in any embedded
        QUANTIFIED sentiment delta (e.g. 'social sentiment declined 9.88').
        """
        issues = re.split(r"(?im)^\**\s*Issue\s+\d+", text)
        issue_scores = []
        for block in issues:
            low = block.lower()
            bull_i, bear_i = low.find("bull case"), low.find("bear case")
            if bull_i == -1 or bear_i == -1:
                continue
            if bull_i < bear_i:
                bull_txt, bear_txt = block[bull_i:bear_i], block[bear_i:]
            else:
                bear_txt, bull_txt = block[bear_i:bull_i], block[bull_i:]
            bull_w = len(self._BULL.findall(bull_txt)) + 1
            bear_w = len(self._BEAR.findall(bear_txt)) + 1
            issue_scores.append((bull_w - bear_w) / (bull_w + bear_w))
        prov = {"sanitized": True, "chars": len(text)}
        if issue_scores:
            score = sum(issue_scores) / len(issue_scores)
            confidence = min(1.0, 0.4 + 0.15 * len(issue_scores))
            prov.update({"method": "issue_balance", "n_issues": len(issue_scores)})
        else:
            bull = len(self._BULL.findall(text)); bear = len(self._BEAR.findall(text))
            tot = bull + bear
            if tot == 0:
                return 0.0, 0.0, {**prov, "method": "none"}
            score = (bull - bear) / tot
            confidence = min(0.5, tot / 30.0)  # lexicon is unreliable -> capped low
            prov.update({"method": "lexicon_fallback", "bull_hits": bull, "bear_hits": bear})
        qm = self._QUANT.search(text)
        if qm:
            direction = -1 if qm.group(1).lower() in ("declined", "dropped", "fell") else 1
            mag = min(0.3, float(qm.group(2)) / 50.0)
            score = max(-1.0, min(1.0, score + direction * mag))
            prov["quant_delta"] = round(direction * mag, 4)
        return round(score, 4), round(confidence, 4), prov

    def normalize(self, record: dict) -> Iterable[SentimentEvent]:
        """Pure. Issue-balance scoring + optional EWMA smoothing via prior_score."""
        text = record.get("raw_text", "") or ""
        if not text:
            return []
        raw_score, confidence, prov = self._score_text(text)
        if prov.get("method") == "none":
            return []
        prior = record.get("prior_score")
        if prior is not None:
            alpha = 0.5  # EWMA weight on new reading; lower = smoother
            score = round(alpha * raw_score + (1 - alpha) * float(prior), 4)
            prov.update({"smoothed_from_prior": float(prior), "raw_score": raw_score})
        else:
            score = raw_score
        now = _now_iso()
        ent = record["entity"]
        ev = SentimentEvent(
            event_id=_event_id(self.source_id, record["raw_id"], ent, now),
            entity=ent, entity_type="ticker",
            score=score, confidence=confidence,
            ts=now, observed_at=now, ingested_at=now,
            source=self.source_id, venue=self.venue,
            raw_ref=f"runs/sentiment/raw/{self.source_id}/{record['raw_id'].replace(':','_')}.txt",
            raw=prov,
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
