# cross_source_sentiment_divergence researched-rung dossier

- **Status:** draft
- **Recommendation:** needs_more_research
- **Signal family:** `cross_source_divergence` in `research/strategy_space.py`; dossier name uses the dispatch alias `cross_source_sentiment_divergence`
- **Candidate coordinates:** proposed tuple family `cross_source_divergence | rh_all_liquid or rh_scanner_movers | 3d-20d | equity/option_watch | capped_notional`; no registry mutation
- **Author / date:** dossier-cross_source_sentiment_divergence-9c39, 2026-06-28
- **Boundary:** offline/propose-only; no live connectors, Robinhood calls, capture, sizing, scanner runs, registry edits, PROPOSED artifacts, or ARMED handoff

## One-line thesis
A large point-in-time gap between slow analyst consensus/target dispersion and faster web-search sentiment may predict 3-20 day sentiment reconciliation, but only if the gap is shown cross-sectionally to lead returns rather than reflect contemporaneous price/news noise.

## Mechanism

- Analysts are slow-moving, institutionally constrained forecasters: rating changes and target revisions are dated, sticky, and often cluster after catalysts, while web-search sentiment can move intraday/daily with public attention and controversy.
- Divergence is economically interesting when one source appears stale relative to another: either the Street is over-anchored while web sentiment has already deteriorated/improved, or web sentiment is a noisy crowd overreaction while analyst consensus remains a slower fundamental anchor.
- The natural horizon is short swing/position research, not intraday execution: 3-20 trading days should be long enough for delayed analyst updates, news digestion, and flows to reconcile, but short enough that the signal is still plausibly about sentiment disagreement rather than new fundamentals.
- The sign is not assumed. A valid test must learn whether convergence tends toward analysts, toward web sentiment, or nowhere. TSLA is an example of the battle-location state, not evidence of edge by itself.

## Prior evidence

All concrete source evidence below is **Computer-captured, point-in-time external evidence committed to this repo**, not fresh sal-bot web or market-data access.

- `runs/strategies/research/README.md` defines this packet as cross-source divergence between social/news/search sentiment and requires a source availability map, lag/quality weighting, a >=30-name selector by default, permutation nulls, circularity guards, and cross-sectional generalization before any `testing` promotion.
- `runs/strategies/research/evidence/README.md` says the committed evidence was captured by Computer around 2026-06-28 01:10 UTC via Perplexity Finance connectors, covers only NVDA/RDDT/TSLA/SNDK, and is a seed sample/data-availability probe rather than a dossier universe.
- `runs/strategies/research/_evidence/2026-06-28_external_evidence.md` identifies TSLA as the cleanest cross-source example: analyst consensus is still `buy`, but with a $24.86 low price target versus $600 high and a comparatively low TSLA web sentiment score near 0.18; NVDA is the opposite example with unanimous bullish analyst consensus and stronger web sentiment.
- Deterministic offline inspection of committed rows shows the four seed names are heterogeneous enough to motivate a test but far too small to validate one: TSLA has 37 analyst rows with 18 bullish, 8 neutral, and 11 bearish observations, target range $24.86-$600, and latest committed web score 0.1755; NVDA has 39/39 bullish analyst rows and latest committed web score 0.4098; RDDT has 24 bullish/13 neutral/0 bearish rows and latest score 0.2406; SNDK has 30 bullish/6 neutral/0 bearish rows and latest score 0.4953.
- `runs/strategies/LADDER.md` is negative evidence against promotion: candidate generation has zero weight, `testing` requires the falsification harness (`min_n`, permutation p<=0.10, circularity guard, cross-sectional generalization >=30% of universe), and only an `edge` thesis can feed any action-producing workflow.

Evidence classification: the committed evidence is a point-in-time, four-name data-availability probe plus narrative worked example. It is not academic evidence, not a backtest, not a cross-sectional study, and not enough to recommend `keep_for_testing` under the dossier contract.

## Data availability without live connectors

Offline data sal-bot can inspect now:

- `runs/strategies/research/evidence/csv/<SYM>_analyst_targets.csv`: dated analyst action/rating/price-target rows for NVDA/RDDT/TSLA/SNDK, with `rating_current`, `rating_prior`, `price_target_current`, `price_target_prior`, and `sentiment`.
- `runs/sentiment/series/TICKER_<SYM>.jsonl`: committed web-search sentiment series for the same seed names, with `captured_at`, `ts`, `score`, `score_raw`, `confidence`, `source`, `price_proxy`, and `event_id`.
- `runs/strategies/research/evidence/csv/<SYM>_ohlcv_90d.csv`: daily OHLCV context for the seed names, useful only for offline return targets and price circularity checks.
- `runs/strategies/research/_evidence/2026-06-28_external_evidence.md` and `runs/strategies/research/evidence/README.md`: provenance, capture timestamp, and explicit warning that four seed names are not breadth.

Limitations:

- The current committed analyst data covers only four symbols and mixes point-in-time snapshot consensus with historical row dates. It can support schema design, not cross-sectional inference.
- Analyst row dates are not enough unless Computer also records capture time, provider publication lag, and whether historical rows are backfilled/revised. A target change discovered from a current provider page may include survivorship and revision bias.
- The committed web series is a live-capture artifact now frozen in git for offline review, but it currently covers only NVDA/RDDT/TSLA/SNDK and has a very short history. It is not enough to estimate stable source lag or event-conditioned behavior.
- `price_proxy` appears inside web sentiment rows and must not enter the feature except as a separately lagged target/check; otherwise the feature can become price-in-disguise.
- sal-bot must not call the underlying finance, web-search, scanner, or Robinhood connectors. Computer must capture any wider point-in-time dataset and commit it before offline testing.

Computer-only data needed later:

- >=30 RH-tradeable liquid US equities/ETFs selected by a pre-registered rule, not by post-hoc controversy.
- For each selected symbol: point-in-time analyst consensus, individual dated rating/target rows, capture timestamp, provider source, and any provider revision/backfill metadata.
- Matching web-search sentiment snapshots with `captured_at`, query/source metadata, coverage counts, confidence, and source-quality fields, sampled on a known schedule.
- Daily OHLCV returns for target horizons, captured separately from sentiment features, with market/sector benchmark returns for neutralization.
- Optional but useful: source-specific web buckets (news vs social/forum vs search summaries) if Computer can capture them consistently; otherwise this dossier should stay limited to analyst-vs-web-search divergence, not all sentiment sources.

## RH-tradeable universe and proxies

Preferred selector before any test:

- Start with `rh_all_liquid` from `research/strategy_space.py` but resolve it to a fixed >=30-name panel before capture: US-listed equities/ETFs available on Robinhood, average daily dollar volume above a pre-set floor, market cap above a pre-set floor for single names, and active analyst coverage of at least 8 analysts.
- Add a controversy/disagreement pre-filter that is computable before returns: analyst target dispersion in the top quartile of the resolved panel, or absolute analyst-vs-web sentiment z-gap above a pre-registered threshold. The threshold must be computed cross-sectionally at capture time, not after seeing returns.
- Use the current seed symbols only as examples/data probes. NVDA/RDDT/TSLA/SNDK do not satisfy breadth, and TSLA must not become the trophy-list anchor.

Tradeability/proxy constraints from `CHARTER.md`:

- Real orders are limited to equities/ETFs and level-2 options structures in the Robinhood Agentic account; crypto is watch-only and index data is data-only.
- Raw divergence is not directly tradeable. The proposed RH proxy is a ranked long/short-or-long-only watchlist over tradeable equities/ETFs after Computer review. Any option expression would need separate liquidity/spread checks and remains out of scope for this dossier.
- Minimum breadth before testing: at least 30 liquid RH-tradeable names with at least 8 analyst observations and at least 10 web sentiment captures each; stronger preference is 50+ names to reduce one-name controversy risk.

## Falsifiers before testing

- **Mechanism falsifier:** kill the mechanism if high divergence names do not show systematic sentiment/return convergence, or if convergence direction flips randomly across names and horizons.
- **Data falsifier:** kill or block if analyst rows are not point-in-time, are revised/backfilled without metadata, lack enough analyst coverage, or cannot be aligned to web sentiment timestamps without lookahead.
- **Circularity/lookahead guard:** construct features using only data captured before the prediction timestamp; exclude `price_proxy` from features; lag analyst rows by known publication/capture availability; compare divergence against prior returns and price momentum to ensure it is not merely a transformed price move.
- **Null model:** require the divergence ranking to beat random-label and within-date symbol-shuffle nulls, plus a placebo using stale/lagged web sentiment and a placebo using analyst target dispersion alone.
- **Cross-sectional generalization:** at least 30% of the resolved universe must show same-direction effect after neutralization, not only TSLA or another single battle name.
- **Capacity/implementation check:** reject if selected names are too illiquid, option spreads erase expected edge, analyst updates arrive after the proposed trade window, or the signal requires acting on untradeable/non-RH symbols.

## Proposed offline eval design

- **Inputs:** committed schema generalized from `runs/strategies/research/evidence/csv/<SYM>_analyst_targets.csv`, `runs/sentiment/series/TICKER_<SYM>.jsonl`, and `runs/strategies/research/evidence/csv/<SYM>_ohlcv_90d.csv`; for the actual eval, Computer should commit a frozen >=30-name panel under a new evidence directory rather than extending this dossier file.
- **Transformation:** at each daily decision timestamp, compute analyst tilt (`bullish=+1`, `neutral=0`, `bearish=-1` weighted by analyst recency), analyst target dispersion (cross-sectional z-score of target standard deviation or high/low spread scaled by price), web sentiment z-score, and divergence `z(analyst_tilt + analyst_target_gap) - z(web_score)` using only prior captures. Missing analyst/web data should produce no signal, not imputed conviction.
- **Targets:** 3d, 5d, 10d, and 20d forward returns from OHLCV close-to-close, neutralized by broad market/sector proxy where available. Exclude same-day post-capture price moves if capture time is after market close ambiguity cannot be resolved.
- **Pass bar:** minimum 30 names and 150 symbol-date observations; permutation p<=0.10 on rank IC or spread return; circularity correlation with prior 1d/5d returns below a pre-registered threshold such as |rho|<0.35; at least 30% of names contributing positive directional evidence; stability across TSLA-excluded and seed-excluded splits.
- **Robustness splits:** analyst-high-dispersion vs low-dispersion, high web-confidence vs low web-confidence, mega-cap vs non-mega-cap, earnings-week excluded vs included, and controversial single-name exclusion (TSLA removed).
- **Failure handling:** if only four seed names are available, run schema validation only and keep the signal at `needs_more_research`; do not run a pseudo-backtest that could be mistaken for evidence.

## Kill / keep decision

Recommendation: `needs_more_research`.

- The mechanism is plausible and distinct from pure mention velocity or analyst-revision breadth: it tests disagreement between independent source families rather than level or acceleration within one source.
- The committed seed evidence demonstrates data availability and a TSLA worked example, but four names cannot satisfy the >=30-name selector or cross-sectional generalization gate.
- Current evidence is not a backtest and not independent academic/practitioner validation of this exact analyst-vs-web-search divergence feature.
- The risk of circularity is material because the web sentiment rows include `price_proxy`, analyst target dispersion can be partly price-scaled, and controversial names often have price/news feedback loops.
- The next correct action is a Computer-side offline evidence capture for a fixed >=30-name panel, followed by a deterministic sal-bot eval proposal or critic pass; not promotion to `testing`, `edge`, `PROPOSED`, or live action.

Required next Computer action if kept: capture and commit a frozen, point-in-time >=30-name RH-tradeable panel with analyst rows, web-search sentiment snapshots, and OHLCV targets using the schema/data needs above, then ask sal-bot for an offline eval/critic PR. No connector work is requested from sal-bot.

Corpse lesson if killed later: cross-source disagreement is attractive narrative alpha, but without point-in-time source timestamps and cross-sectional breadth it collapses into a TSLA anecdote and price/news circularity.

## Risks and open questions

- Analyst target pages may be survivorship-biased or revised; historical row `date` does not prove when Computer could have known the row.
- Web-search sentiment source composition may change over time; without source-bucket metadata, divergence may measure search corpus drift rather than investor sentiment.
- TSLA can dominate intuition because it is famous, liquid, controversial, and analyst-dispersed. Any result that fails a TSLA-excluded split should be considered non-general.
- The sign may be regime-dependent: web may lead analysts in fast controversy regimes, while analysts may anchor noisy crowd overreaction in slower fundamental regimes.
- The signal may be redundant with analyst-revision breadth, mention velocity, or price momentum; evals must measure incremental value against those baselines.
- RH implementation requires separate liquidity, spread, and timing checks before any trade expression, especially for options. This dossier does not authorize sizing or execution.
