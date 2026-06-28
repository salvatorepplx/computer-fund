# mention_velocity_acceleration researched-rung dossier

- **Status:** ready_for_computer_review
- **Recommendation:** needs_more_research
- **Signal family:** `mention_velocity` / proposed stricter feature `mention_velocity_acceleration`
- **Candidate coordinates:** `TH-703f03ad99` (`mention_velocity` on `rh_crypto_proxies` @ `1d`, `pair_neutral`/`kelly_capped`) plus proposed selector `rh_attention_liquid_30`
- **Author / date:** dossier-mention_velocity_acceleration-1344, 2026-06-28
- **Boundary:** offline/propose-only; no live connectors, Robinhood calls, capture, sizing, `runs/PROPOSED/`, or ARMED handoff

## One-line thesis
If public attention coverage accelerates before price and exchange volume, then a point-in-time second difference of source coverage (`n_docs` / `n_explicit`) should forecast 1d-5d continuation or exhaustion after neutralizing contemporaneous returns, realized volatility, and OHLCV volume spikes.

## Mechanism
- Attention acceleration can matter when non-institutional or slower discretionary capital first notices a ticker: search/news/social coverage rises, watchlists and options interest follow, and order flow arrives after the first information pulse.
- The signal should be strongest over intraday-5d horizons, not months: attention decay is fast, but retail/information diffusion and dealer hedging can spill into the next sessions.
- The mechanism is not “more bullish news means price up”; it is “coverage count is changing faster than price/volume can explain.” If attention only jumps after price gaps or earnings headlines, the effect is circular and should be killed.
- Continuation and reversal are both plausible. The pre-test design should specify two labels: positive acceleration with low contemporaneous return predicts continuation; positive acceleration after an extreme same-day return/volume shock predicts exhaustion/reversal.

## Prior evidence
- **Repo-local mechanism prior:** `research/strategy_space.py` includes `mention_velocity` with web-search data and the description “acceleration of mention/coverage volume predicts move,” so this is an existing grammar family, not a new live-state mutation.
- **Computer-captured point-in-time evidence:** `runs/strategies/research/evidence/README.md` maps this signal to committed sentiment series `runs/sentiment/series/TICKER_<SYM>.jsonl` and identifies `n_docs`/coverage per capture as the intended mention-volume proxy, with OHLCV volume as a corroborating market-attention proxy. This evidence was captured by Computer at 2026-06-27 ~18:10 PDT / 2026-06-28 ~01:10 UTC from Realtime Finance Data connectors and committed for offline use.
- **Committed sample evidence:** the seed OHLCV files contain 62 daily rows for NVDA, RDDT, TSLA, and SNDK (`*_ohlcv_90d.csv`) and therefore can support deterministic volume-spike and return-regime controls. The committed web sentiment JSONL files cover only four seed tickers and roughly 15-34 rows per ticker across 2026-06-26 to 2026-06-28.
- **Negative evidence / current blocker:** the current committed `runs/sentiment/series/TICKER_<SYM>.jsonl` rows do not include `n_docs` or `n_explicit` fields, even though `execution/web_sentiment.py` defines them in `WebSentimentResult`. The persisted rows include sentiment scores, timestamps, source, event IDs, and `price_proxy`; using row counts, event IDs, or score changes as a substitute for document coverage would confound capture cadence and price-linked sentiment with mention volume.
- **Evidence classification:** current evidence is repo-local mechanism evidence plus Computer-captured static data-availability probes. It is not a cross-sectional backtest, academic prior, or live readiness proof. Under the dossier contract, it is insufficient for `keep_for_testing` until at least three independent sources or a larger committed point-in-time sample exist.

## Data availability without live connectors
- **Available to sal-bot now:** `runs/strategies/research/README.md`, `runs/strategies/LADDER.md`, `research/strategy_space.py`, `CHARTER.md`, committed OHLCV CSVs under `runs/strategies/research/evidence/csv/`, committed external-evidence notes, and historical sanitized sentiment JSONL under `runs/sentiment/series/`.
- **Available fields now:** sentiment rows expose `ts`, `captured_at`, `entity`, `score` / `score_raw`, `confidence`, `source`, `event_id`, and `price_proxy`; OHLCV exposes daily `date`, `open`, `high`, `low`, `close`, and `volume`.
- **Missing for this signal:** persisted attention-count fields `n_docs`, `n_explicit`, and source-domain composition per capture. Without them, acceleration cannot be constructed as a coverage-count feature.
- **Timestamp risks:** web-search results can contain article dates that differ from capture time; the eval must use capture timestamp for feature availability and must reject rows whose source document date is after the simulated decision time.
- **Revision/survivorship risks:** live search pages and financial summaries are mutable; Computer must commit append-only raw capture artifacts or normalized count fields at each point in time rather than letting workers reconstruct history from current pages.
- **Point-in-time gap:** the four seed names are only data probes. They cannot satisfy the default >=30-name breadth expectation or the >=30% universe-generalization gate.

## RH-tradeable universe and proxies
- **Proposed selector:** `rh_attention_liquid_30` = at least 30 RH-tradeable US equities/ETFs selected before testing from high-liquidity names with regular web-search coverage, minimum median dollar volume, and no hard-coded outcome-based membership. Candidate discovery is Computer-side because RH scanner/live web capture is outside sal-bot boundaries.
- **Seed names are not the universe:** NVDA, RDDT, TSLA, and SNDK are worked examples / data-availability probes only. Four names cannot establish cross-sectional edge.
- **Proxy:** if the raw attention feature is source coverage, the tradeable instrument is the underlying RH equity/ETF. Options can be analyzed later only as implementation overlays under `CHARTER.md` Level-2 constraints; this dossier does not authorize options or any execution.
- **Breadth before testing:** minimum 30 liquid RH-tradeable names; at least 30% of the resolved universe must show the same directional effect after holdout, not merely one trophy ticker.
- **Basis risk:** web mention coverage can be about macro/sector themes, lawsuits, product launches, or earnings rather than ticker-specific tradable attention. Entity matching must reject ambiguous bare terms and require `TICKER:<SYM>` normalized entities.

## Falsifiers before testing
- **Mechanism falsifier:** kill if attention acceleration has no positive lead over future returns once same-day return, overnight gap, realized volatility, earnings days, analyst-revision days, and OHLCV volume shock are controlled.
- **Data falsifier:** kill or keep blocked if Computer cannot persist point-in-time `n_docs`, `n_explicit`, and source-domain counts for at least 30 liquid RH-tradeable names with stable timestamps and raw-capture auditability.
- **Circularity/lookahead guard:** regress attention acceleration against contemporaneous absolute return, price gap, and volume z-score; kill if the feature is mostly explained by price/volume or if removing rows whose docs mention price moves erases the effect.
- **Null model:** require entity-wise timestamp permutation, random-label placebo, and source-count cadence placebo. The feature must beat a null that preserves each ticker's capture schedule and price series while shuffling attention counts within ticker.
- **Cross-sectional generalization:** require the effect on >=30% of the resolved universe and no single ticker/sector contributing more than a pre-specified share of total signal P&L or rank IC.
- **Capacity/implementation check:** reject if the apparent edge concentrates in names with poor spreads, event halts, unavailable RH trading, post-close-only capture, or volume spikes so extreme that next-session entry is unrepresentative.

## Proposed offline eval design
- **Inputs:** append-only JSONL rows with `entity`, `captured_at`, `n_docs`, `n_explicit`, source-domain count map, sentiment score, and `price_proxy`; daily/intraday OHLCV volume and close data with point-in-time availability; optional raw-result IDs for audit.
- **Transformation:** per ticker, sort by `captured_at`; compute coverage velocity `d_docs = n_docs_t - n_docs_{t-1}` and acceleration `dd_docs = d_docs_t - d_docs_{t-1}`; normalize by trailing capture-window median and source count; winsorize extreme counts; mark missing counts as unavailable rather than zero.
- **Volume proxy controls:** compute OHLCV volume z-score vs trailing 20 trading days and same-horizon return; test attention acceleration both standalone and residualized against volume z-score and absolute return.
- **Targets:** 1d, 3d, and 5d forward close-to-close returns, plus benchmark/sector-neutral residuals where possible. Exclude labels overlapping the capture window and exclude post-event rows where earnings/known scheduled events make attention mechanically jump.
- **Pass bar:** before any `testing` promotion, require at least 30 resolved names, at least 24 time-spaced observations per name or the relevant harness floor, permutation p <= 0.10, circularity beta/R² below a pre-specified threshold, and >=30% universe hit-rate on holdout.
- **Robustness splits:** test by source mix, large-cap vs mid-cap, earnings vs non-earnings windows, high-volume vs normal-volume regimes, and continuation vs reversal label definitions.

## Kill / keep decision
- **Recommendation: needs_more_research.** The mechanism is plausible and already represented in the strategy grammar, but the required coverage-count fields are not currently persisted in committed series.
- Four seed names and 15-34 sentiment rows per ticker are data probes, not breadth; this cannot support a cross-sectional edge claim.
- OHLCV volume is useful as a corroborating attention proxy and circularity control, but it cannot replace independent mention-count acceleration without becoming price/volume momentum in disguise.
- Required next Computer action: if Computer wants this signal considered for `testing`, commit a wider point-in-time fixture for a predeclared >=30-name RH-liquid selector with persisted `n_docs`, `n_explicit`, source-domain counts, raw-capture audit references, and aligned OHLCV volume/return labels.
- If Computer cannot persist those fields point-in-time, add the corpse lesson: “mention velocity without stored coverage counts collapses into capture cadence or price-linked sentiment and is not a distinct signal.”

## Risks and open questions
- The existing normalized series includes `price_proxy`; any score or count field derived from search snippets that mention stock-price moves can leak price into the feature.
- Capture cadence can masquerade as acceleration if more rows are collected during exciting periods; evals must preserve cadence in nulls and use per-capture counts, not row counts.
- `n_docs` may be capped by search-result limits, causing saturation exactly when attention is highest.
- Source composition matters: one domain repeating “bullish” across snippets is not the same as broad independent attention.
- The correct sign may be regime-dependent: early attention acceleration can continue, late attention acceleration after large price/volume shocks can reverse.
- Computer-side data need is explicit: sal-bot cannot run web/search capture, RH scanners, finance connectors, or live market feeds; all wider universe selection and point-in-time external capture must be performed and committed by Computer.
