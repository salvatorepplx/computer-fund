"""
One-shot sentiment+price capture built on the WEB-SEARCH sentiment substrate
(pplx_sdk), replacing the flaky finance_ticker_sentiment connector (401s under
load, static summarizer). The web corpus is reliable, no-auth, timestamped, and
moves between captures as news moves — a real signal to predate.

Appends one observed point to runs/sentiment/series/<ENTITY>.jsonl, same schema
as before so all downstream code (ingest_runner, lead-lag falsifier) is unchanged.

Usage: python scripts/capture_web_tick.py TICKER:NVDA NVDA
Run with api_credentials=["pplx-sdk"] (search) and optionally ["external-tools"] (price).
"""
from __future__ import annotations
import sys, json, subprocess, datetime as dt, hashlib, re, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from execution.web_sentiment import WebSearchSentimentSource, normalize
from execution.ingest_runner import append_observation, series_length, load_series
from execution.sentiment_adapters import persist_raw

import pplx_sdk


def web_search(queries: list[str], limit: int = 6) -> list[dict]:
    """Run the source's queries via pplx_sdk and flatten into a corpus of docs."""
    corpus: list[dict] = []
    seen = set()
    for q in queries:
        try:
            hits = pplx_sdk.search.web(q, limit=limit)
        except Exception as e:
            print(f"[warn] search failed for {q!r}: {str(e)[:120]}")
            continue
        for h in hits:
            d = dict(h)
            url = d.get("url", "")
            if url in seen:
                continue
            seen.add(url)
            corpus.append({
                "title": d.get("title", ""),
                "summary": d.get("summary") or d.get("snippet") or "",
                "domain": d.get("domain", ""),
                "date": d.get("date", ""),
                "url": url,
            })
    return corpus


def _price_from_robinhood(symbol: str):
    """Best-effort live price via robinhood (often 401s; never fatal)."""
    payload = json.dumps({"source_id": "robinhood", "tool_name": "get_equity_quotes",
                          "arguments": {"symbols": [symbol]}})
    try:
        out = subprocess.run(["external-tool", "call", payload],
                             capture_output=True, text=True, timeout=60)
        if out.returncode == 0 and out.stdout.strip():
            q = json.loads(out.stdout)
            res = q["data"]["results"][0]["quote"]
            return float(res.get("last_non_reg_trade_price") or res.get("last_trade_price"))
    except Exception as e:
        print(f"[warn] robinhood price unavailable: {str(e)[:100]}")
    return None


# A $-figure with CENTS (e.g. $195.74) is far more likely a live quote than a
# round number ($300 target, $5 EPS). Capture position so we can weight by context.
_PRICE_RX = re.compile(r"\$\s?([0-9]{1,4}(?:\.[0-9]{1,2})?)")
# price-context cue words; a $-figure near these is much more likely the real quote
_CTX = re.compile(r"(closed at|trading (?:at|near|around)|last (?:trade|price)|"
                  r"current(?:ly)?|price|shares?|opened at|changed hands|quote|"
                  r"after[- ]hours|pre[- ]market|prev(?:ious)? close|at close)", re.I)

def _price_from_corpus(corpus: list[dict], symbol: str):
    """Context-aware live-price proxy from the web corpus.

    Financial text is full of NON-price $-figures (price targets, EPS, P/E,
    52w highs, small-cap mentions) so a blind median fails on bimodal corpora
    (e.g. SNDK: small EPS/% figures + real ~$500-1700 quotes -> median lands at junk).

    Strategy: score each $-figure by context and prefer real quotes:
      +3 if it has cents (e.g. .74)         -> quotes almost always do
      +2 if a price-context cue is within ~40 chars
      +2 if the ticker symbol is within ~50 chars
    Take the median of the HIGHEST-scoring tier; fall back to all if none score.
    """
    scored: list[tuple[int, float]] = []
    sym = symbol.upper()
    for doc in corpus:
        text = f"{doc.get('title','')} {doc.get('summary','')}"
        for m in _PRICE_RX.finditer(text):
            raw = m.group(1)
            try:
                v = float(raw)
            except ValueError:
                continue
            if not (5.0 <= v <= 5000.0):
                continue
            s, e = m.start(), m.end()
            window = text[max(0, s - 45):min(len(text), e + 45)]
            score = 0
            if "." in raw:
                score += 3
            if _CTX.search(window):
                score += 2
            if sym in window.upper():
                score += 2
            scored.append((score, v))
    if not scored:
        return None
    top = max(s for s, _ in scored)
    # require a meaningful context score (>=2) to trust; else fall back to cents-only
    if top >= 2:
        tier = [v for s, v in scored if s == top]
    else:
        cents = [v for s, v in scored if s >= 3]
        tier = cents or [v for _, v in scored]
    return round(statistics.median(tier), 2)


def get_price(symbol: str, corpus: list[dict], last_price: float | None = None):
    """Primary: web corpus (reliable). Fallback: robinhood quote.

    Series-consistency gate: reject a corpus price that deviates >35% from the
    last good price for this name (real intraday moves between captures rarely
    exceed that; a big jump means an extraction error on a noisy corpus, e.g.
    a price-target or EPS figure leaking through). Protects every name generically.
    """
    p = _price_from_corpus(corpus, symbol)
    if p is not None:
        if last_price and last_price > 0 and abs(p - last_price) / last_price > 0.35:
            # extraction looks wrong vs history -> distrust corpus, try broker, else hold last
            rb = _price_from_robinhood(symbol)
            if rb is not None:
                return rb, "robinhood"
            return last_price, "held_last(corpus_rejected)"
        return p, "corpus"
    rb = _price_from_robinhood(symbol)
    if rb is not None:
        return rb, "robinhood"
    return (last_price, "held_last") if last_price else (None, "none")


def canonical_entity(entity: str, symbol: str) -> str:
    """Canonicalize the entity ID so the series file is stable no matter how the
    script is invoked (e.g. 'nvda', 'NVDA', 'TICKER:NVDA' all -> 'TICKER:NVDA').
    Prevents the split-series bug where lowercase args wrote to a parallel file.
    """
    e = (entity or "").strip()
    if ":" in e:
        prefix, sym = e.split(":", 1)
        return f"{prefix.upper()}:{sym.upper()}"
    # bare symbol given as entity -> treat as a TICKER
    sym = (e or symbol).upper()
    return f"TICKER:{sym}"


def capture(entity: str, symbol: str, name: str = "") -> dict:
    entity = canonical_entity(entity, symbol)
    src = WebSearchSentimentSource(search=web_search)
    corpus = src.fetch(symbol, name)
    if not corpus:
        return {"captured": False, "reason": "empty web corpus"}

    # persist raw corpus by reference (sanitized: titles+summaries only)
    now = dt.datetime.now(dt.timezone.utc)
    rid = f"{symbol}:{now.strftime('%Y-%m-%dT%H%M')}"
    persist_raw("web_search_sentiment", rid, json.dumps(corpus)[:20000])

    # EWMA smoothing against last observed score
    prior = None
    series = load_series(entity)
    if series:
        prior = series[-1].get("score")
    r = normalize(corpus, prior_score=prior)
    raw = normalize(corpus, prior_score=None)  # unsmoothed, for responsive lead-lag

    obs_at = now.isoformat()
    eid = "sha256:" + hashlib.sha256(f"web:{rid}:{entity}:{obs_at}".encode()).hexdigest()[:16]
    ev = {
        "event_id": eid, "entity": entity, "entity_type": "ticker",
        "score": r.score, "score_raw": raw.score, "confidence": r.confidence,
        "ts": obs_at, "observed_at": obs_at, "ingested_at": obs_at,
        "source": "web_search_sentiment", "venue": "web.search",
        "raw_ref": rid, "raw": {"sanitized": True, "n_docs": r.n_docs,
                                "n_explicit": r.n_explicit, "method": r.method},
    }

    last_price = None
    if series:
        for _r in reversed(series):
            if _r.get('price_proxy'):
                last_price = _r['price_proxy']; break
    price, price_src = get_price(symbol, corpus, last_price)
    ev["raw"]["price_src"] = price_src
    ref = append_observation(entity, ev, price_proxy=price)
    return {"captured": True, "entity": entity, "score": r.score,
            "confidence": r.confidence, "n_docs": r.n_docs,
            "n_explicit": r.n_explicit, "method": r.method,
            "price_proxy": price, "price_src": price_src, "series_path": ref,
            "series_length": series_length(entity)}


if __name__ == "__main__":
    entity = sys.argv[1] if len(sys.argv) > 1 else "TICKER:NVDA"
    symbol = sys.argv[2] if len(sys.argv) > 2 else "NVDA"
    name = sys.argv[3] if len(sys.argv) > 3 else ""
    print(json.dumps(capture(entity, symbol, name), indent=2))
