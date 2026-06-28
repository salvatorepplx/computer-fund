# Spike: pplx_sdk.llm.extract vs the regex/lexical bull-bear scorer

**Date:** 2026-06-28 · **Author:** Computer · **Status:** validated finding, propose-only (no live swap yet)
**Script:** `scripts/spike_llm_extract.py` (run with api_credentials=["pplx-sdk"])

## Why
The self-audit flags the `signal` axis as single-source + brittle. `execution/web_sentiment.py` scores
sentiment with regex + lexical bull/bear term balance. `pplx_sdk.llm.extract` (schema-based extraction)
is an unused capability that could replace it. Tested empirically before proposing.

## Result (NVDA, 22-doc live corpus, 2026-06-28)
- **Regex/lexical scorer:** score=+0.2293, conf=0.95, n_explicit=10.
- **llm.extract (conf-weighted aggregate over 22 docs):** score=+0.0939.
- **Delta (llm − regex): −0.1354.**

Per-doc, llm.extract is far more discriminating and correctly calibrated:
- Generic quote/boilerplate pages (CNBC quote, Robinhood quote, MarketWatch quote) → **neutral 0.0**.
- "Nvidia Beats Back Bubble Fears With Record $68B in Sales" → **bullish +0.85**.
- "NVDA Stock Forecast & Price Prediction 2026-2030" → **bearish −0.70**.
- "Bull & Bear case of NVDA" → bearish −0.30; "YouTube Analyst Bull vs Bear Debate" → +0.52.

## Finding (chip on the shoulder)
The regex scorer is **systematically over-bullish**: it treated 10 boilerplate/quote pages as "explicit"
high-confidence readings, inflating the score to +0.23 when an honest semantic read of the same corpus is
+0.09. An over-bullish sentiment input feeding the lead-lag thesis is exactly the kind of hidden bias that
could manufacture a false EDGE. This is direct evidence the signal-quality axis needs the upgrade.

## Proposed next step (not done yet — needs care)
1. Add `WebSearchSentimentSource` mode that uses `llm.extract` per doc with the bull/bear schema, keeping
   `normalize()` pure by injecting the extractor (same DI pattern as the search callable).
2. Offline tests: feed synthetic docs, assert calibration (boilerplate→~0, explicit bull→+, explicit bear→−).
3. Do NOT hot-swap mid-thesis on the live series — run llm.extract in PARALLEL (`score_llm` alongside
   `score_raw`) for a burn-in so the change is measured, not assumed. Only promote after the parallel
   series shows the llm score is better-calibrated and the lead-lag/permutation verdict is re-evaluated.
4. `llm.extract_many` for batched cross-sectional scoring (ties into STRAT-WIDE ≥30%-universe gate).
