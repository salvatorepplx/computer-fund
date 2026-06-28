# vol_regime_gated_reversion researched-rung dossier

- **Status:** ready_for_computer_review
- **Recommendation:** needs_more_research
- **Signal family:** `vol_regime_gate` (`price_only`)
- **Candidate coordinates:** `TH-eca9936909` (`rh_crypto_proxies`, `1w`, `regime_overlay`, `equal_weight`); broader proposed selector below because four proxies are not breadth
- **Author / date:** dossier-vol_regime_gated_reversion-73ce, 2026-06-28
- **Boundary:** offline/propose-only; no live connectors, Robinhood calls, capture, sizing, or ARMED handoff

## One-line thesis
A liquid Robinhood-tradeable name that makes a large short-horizon move should mean-revert over the next 1-5 trading days only when its trailing realized volatility is in a pre-registered high-volatility regime; in low-volatility regimes, the same move should not show the same reversion edge.

## Mechanism
- Volatility regimes proxy for who is forced to trade: high realized volatility can reflect crowded de-risking, option-market hedging, stop-loss cascades, and liquidity-taker urgency, creating temporary overshoots that later mean-revert.
- The signal should predict future returns only if the regime variable identifies temporary price pressure, not simply that the asset is volatile. The economic bet is that a recent extreme return is more likely to be an overshoot when realized vol is already elevated.
- The natural horizon is short, pre-registered at 1d, 3d, and 5d, because the hypothesized pressure-release mechanism should decay once liquidity providers, systematic rebalancers, and discretionary dip-buyers/faders absorb the move.
- This is not a momentum thesis unless the offline test shows the opposite sign. If high-volatility large moves continue rather than reverse, the mechanism is wrong for `reversion` and should be killed or reframed as a separate momentum-regime thesis.

## Prior evidence
- **Committed Computer-captured OHLCV evidence, point-in-time as of 2026-06-28:** `runs/strategies/research/evidence/csv/*_ohlcv_90d.csv` contains 62 daily rows each for NVDA, RDDT, SNDK, and TSLA from 2026-03-30 through 2026-06-26. These snapshots are enough to verify field shape and prototype realized-volatility construction, but not enough to infer an edge.
- **Observed seed dispersion from committed OHLCV:** using close-to-close log returns, 20d annualized realized-vol ranges are materially different across the four seed names: NVDA roughly 27%-46%, RDDT 60%-86%, SNDK 80%-132%, and TSLA 35%-49%. SNDK is the extreme probe, with about +265% total return over the 62-row window and a maximum one-day absolute close-to-close move near 20%.
- **Committed mechanism note:** `runs/strategies/research/_evidence/2026-06-28_external_evidence.md` identifies this mechanism's intended data path as `finance_ohlcv_histories`, with realized-vol percentile regimes, reversion conditional on regime, a permutation-of-regime-labels null, and a cross-sectional generalization bar of at least 30% of the universe.
- **Research-standard evidence gap:** no academic, exchange/regulatory, or independent practitioner paper for this exact vol-regime-gated reversion mechanism is committed in the repo. Under `runs/strategies/research/README.md`, that prevents a `keep_for_testing` recommendation until Computer or a future worker commits at least three source records or an equivalent literature digest for review.
- **Evidence type classification:** current evidence is data-availability and seed-dispersion evidence, not cross-sectional edge evidence. It is neither a time-series backtest nor a breadth test.

## Data availability without live connectors
- Available now to sal-bot: four committed OHLCV CSV snapshots with `date`, `open`, `high`, `low`, `close`, and `volume` columns under `runs/strategies/research/evidence/csv/`; the dossier contract in `runs/strategies/research/README.md`; the strategy ladder in `runs/strategies/LADDER.md`; the generated coordinate grammar in `research/strategy_space.py`; and Computer-captured point-in-time evidence notes under `runs/strategies/research/_evidence/`.
- The current OHLCV snapshots appear daily and point-in-time to the capture commit, but the dossier cannot verify split/dividend adjustment policy, delisting coverage, corporate-action handling, exchange calendar alignment, or whether rows are as-of-close values available before the target horizon starts.
- The 90-calendar-day snapshots provide only 62 trading rows, which is insufficient for rolling-vol percentile estimates that are stable across regimes. A 20d realized-vol estimate inside 62 rows leaves roughly 42 usable feature rows per name before any target-horizon drop.
- No live data is needed for the dossier, but Computer would need later connector/capture work to commit a wider historical OHLCV panel. sal-bot should not call `finance_ohlcv_histories`, Robinhood scanners, live web/search capture, or any live market/account/order API.
- Data path if continued: Computer commits split-adjusted daily OHLCV plus corporate-action metadata for a pre-registered universe, with explicit capture timestamp and source provenance. sal-bot can then run deterministic offline feature construction against the committed files.

## RH-tradeable universe and proxies
- The current generated coordinate `TH-eca9936909` uses `selector:fixed(COIN,MSTR,MARA,RIOT)` as crypto-beta equities. That is a valid RH-tradeable proxy for crypto exposure because crypto itself is watch-only under `CHARTER.md`, but four names are not enough for cross-sectional breadth.
- Minimum selector for a real test: `selector:liquid_us_equities_etfs(price >= $5, median_20d_dollar_volume >= $20M, >=252 prior daily bars, RH-tradeable equity or ETF, no live account/order interaction)`, then sample or rank at least 30 names stratified across trailing 60d realized-volatility terciles.
- Preferred first breadth universe: at least 30 liquid, high-attention single-name equities and ETFs from `rh_all_liquid` or `rh_scanner_movers`, not a hand-picked trophy list. Sector/index ETFs can be included as a placebo sleeve but should not dominate the sample because ETF reversion mechanisms differ from single-stock crowding and hedging.
- If Computer wants to preserve the crypto-proxy coordinate, expand it only if at least 30 RH-tradeable crypto-beta or high-beta proxy equities/ETFs can be selected by an objective rule. If not, treat `TH-eca9936909` as data-blocked for breadth and test the signal family on a broader liquid-RH selector first.
- Options are not required for testing. If later expressed with options, option liquidity and spread stress must be a separate implementation gate; this dossier only supports price-only equity/ETF return tests.

## Falsifiers before testing
- **Mechanism falsifier:** high-volatility regimes do not increase the magnitude or frequency of next-1d/3d/5d reversal after large prior moves, or the sign is continuation rather than reversion across most volatility strata.
- **Data falsifier:** OHLCV cannot be proven point-in-time, split-adjusted, and available before the prediction horizon; fewer than 30 names or fewer than 250 prior bars per name are committed; or missing/delist rows are silently dropped.
- **Circularity/lookahead guard:** trailing realized vol at decision date `t` must use returns through `t-1` only, and the trigger return must be fully known before the target return begins. No feature may use `close_t` to trade at `close_t` unless the target starts at the next open and slippage is modeled.
- **Null model:** shuffle regime labels within each name and rerun the reversal rule; also run random-label targets and date-block permutations so autocorrelation and clustered volatility do not create fake significance.
- **Cross-sectional generalization:** at least 30 names must be eligible, and at least 30% of names must show the pre-registered effect direction after costs; the effect cannot come from only SNDK-like outliers.
- **Capacity/implementation check:** the result must survive 15 bps round-trip cost, next-open entry instead of same-close entry, volume participation caps, and exclusion of earnings +/-1 trading day to avoid confusing event drift with vol-regime reversion.

## Proposed offline eval design
- **Inputs:** one CSV per symbol with `date,open,high,low,close,volume`; required future schema additions are `symbol`, `capture_asof`, `adjustment_policy`, and optional `split_factor`/`dividend` metadata. Current seed files may be used only for parser and feature-shape smoke tests.
- **Transformation:** compute close-to-close log returns; compute trailing 20d and 60d realized volatility using rows ending at `t-1`; assign within-name rolling percentile regimes using only prior observations; define an extreme prior move as absolute 1d return above the name's trailing 80th or 90th percentile.
- **Signal:** for high-vol regime and extreme positive move, predict negative next-horizon return; for high-vol regime and extreme negative move, predict positive next-horizon return. Low-vol regimes are the contrast group, not optional cherry-picked exclusions.
- **Targets:** next 1d, 3d, and 5d close-to-close or next-open-to-close returns, benchmark-neutralized by SPY/sector ETF where available. Exclude overlapping labels or use block bootstrap / clustered standard errors so 3d and 5d horizons do not inflate N.
- **Pass bar:** at least 30 eligible names, at least 250 pre-signal daily bars per name, at least 200 total non-overlapping events, permutation p-value <= 0.10 after multiple-testing visibility, positive post-cost reversal spread in at least 30% of names, and no single name contributing more than 20% of gross edge.
- **Robustness splits:** pre-register splits by realized-vol tercile, liquidity tercile, single-name vs ETF, earnings-excluded days, and first-half vs second-half date ranges.

## Kill / keep decision
- **Recommendation: `needs_more_research`.** The economic mechanism is plausible enough to preserve, but the committed evidence is only four seed OHLCV probes and a data-path note.
- The four committed names demonstrate that realized-vol regimes can be computed offline, but they do not establish breadth, persistence, or a reversion edge.
- `TH-eca9936909` is especially breadth-blocked because its fixed crypto-proxy universe has four symbols; generation is not evidence and four symbols are not a cross-sectional thesis.
- The dossier lacks three independent mechanism/prior sources required by the research contract for `keep_for_testing`.
- Required next Computer action if kept: commit a point-in-time, split-adjusted daily OHLCV panel for the pre-registered >=30-name liquid-RH selector, plus source/adjustment metadata and any literature/practitioner evidence Computer wants sal-bot to cite. This is a data/research request, not an execution, sizing, or ARMED request.

## Risks and open questions
- The most likely false positive is price-in-disguise: realized vol and large recent returns are both transformations of price, so the nulls must prove the regime gate adds information beyond a generic reversal rule.
- Volatility clustering can make shuffled single-day nulls too easy; use within-name block permutations or regime-label permutations that preserve run lengths.
- SNDK-like explosive trends can dominate a small panel and make reversion look good or bad depending on endpoint choice; concentration and leave-one-name-out checks are mandatory.
- Corporate actions, ticker changes, splits, and stale OHLCV adjustment policy can fabricate returns unless Computer commits adjustment metadata.
- The RH-tradeable universe is time-varying; testing current constituents over past data creates survivorship bias unless the first offline version is clearly labeled as a prototype and later upgraded to point-in-time constituents.
- If the effect exists only in distressed microcaps or option-illiquid names, it may be untradeable under realistic spread, slippage, and cash-account settlement constraints.
