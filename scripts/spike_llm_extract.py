"""
SPIKE: validate pplx_sdk.llm.extract as a structured bull/bear sentiment scorer,
to compare against the regex/lexical scorer in execution/web_sentiment.py.

This is a propose/validate spike — it does NOT write to the observed series.
Run with api_credentials=["pplx-sdk"].
"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pplx_sdk
from execution.web_sentiment import WebSearchSentimentSource, normalize


def web_search(queries, limit=6):
    corpus, seen = [], set()
    for q in queries:
        try:
            hits = pplx_sdk.search.web(q, limit=limit)
        except Exception as e:
            print(f"[warn] search failed {q!r}: {str(e)[:100]}")
            continue
        for h in hits:
            d = dict(h)
            u = d.get("url", "")
            if u and u in seen:
                continue
            seen.add(u)
            corpus.append(d)
    return corpus


SCHEMA = {
    "type": "object",
    "properties": {
        "stance": {"type": "string", "enum": ["bullish", "bearish", "neutral", "mixed"]},
        "score": {"type": "number", "description": "sentiment from -1 (max bearish) to +1 (max bullish)"},
        "confidence": {"type": "number", "description": "0..1 confidence"},
        "rationale": {"type": "string", "description": "one sentence why"},
    },
    "required": ["stance", "score", "confidence"],
}

INSTRUCTION = (
    "You are scoring market sentiment for a single stock from one news/search result. "
    "Read the title and summary. Output the bull/bear stance, a numeric score in [-1,1] "
    "(positive=bullish), a confidence in [0,1], and a one-sentence rationale. "
    "Be calibrated: routine coverage is near 0; only strong, explicit bull/bear language is extreme."
)


def main():
    sym = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    src = WebSearchSentimentSource(search=web_search)
    queries = src.queries_for(f"TICKER:{sym}", sym) if hasattr(src, "queries_for") else [
        f"{sym} stock bull vs bear today", f"{sym} stock price news today"]
    corpus = web_search(queries, limit=5)
    print(f"corpus: {len(corpus)} docs for {sym}\n")

    # --- regex/lexical baseline (current live scorer) ---
    base = normalize(corpus)
    print(f"REGEX/LEXICAL scorer: score={base.score:+.4f} conf={base.confidence:.2f} "
          f"method={base.method} n_explicit={base.n_explicit}")

    # --- llm.extract per doc, then aggregate ---
    items = [f"{d.get('title','')} . {d.get('summary', d.get('snippet',''))}" for d in corpus]
    if not items:
        print("no docs; abort")
        return
    results = pplx_sdk.llm.extract(items=items, instruction=INSTRUCTION, output_schema=SCHEMA)
    scores, confs = [], []
    print("\nper-doc LLM extractions:")
    for d, r in zip(corpus, results):
        data = (getattr(r, "result", None) or {}) if not getattr(r, "error", None) else {}
        s = data.get("score"); c = data.get("confidence"); st = data.get("stance") or "?"
        if s is not None:
            scores.append(float(s)); confs.append(float(c if c is not None else 0.5))
        print(f"  [{st:>8}] score={s} conf={c} :: {(d.get('title','') or '')[:70]}")
    if scores:
        # confidence-weighted mean
        wsum = sum(confs) or 1.0
        agg = sum(s*c for s, c in zip(scores, confs)) / wsum
        print(f"\nLLM-EXTRACT aggregate (conf-weighted): score={agg:+.4f} over n={len(scores)} docs")
        print(f"\nDELTA (llm - regex): {agg - base.score:+.4f}")


if __name__ == "__main__":
    main()
