# short_interest_squeeze_asymmetry researched-rung dossier

- **Status:** ready_for_computer_review
- **Recommendation:** needs_more_research
- **Signal family:** `short_interest_squeeze` from `research/strategy_space.py`
- **Candidate coordinates:** `TH-db74dc5860` (`short_interest_squeeze` on `rh_index_etfs` @ `5d`, `pair_neutral`/`kelly_capped`) is the generated coordinate; this dossier instead recommends the more appropriate selector `rh_high_short` before any test.
- **Author / date:** dossier-short_interest_squeeze_asymmetry-bab7, 2026-06-28
- **Boundary:** offline/propose-only; no live connectors, web-search capture, Robinhood calls, live market/account/order/execution APIs, sizing, `runs/PROPOSED/`, or ARMED handoff. Evidence below is limited to committed repo artifacts and Computer-captured point-in-time snapshots.

## One-line thesis
High and rising short interest plus a positive catalyst or attention shock may create convex 1d-5d upside because crowded shorts and hedged longs have to buy into scarce float, but the signal is not testable yet without point-in-time short-interest, float, and borrow-pressure data.

## Mechanism
- The economic story is not simply "high short interest means stock goes up." It is an asymmetry story: when short exposure is crowded relative to float and normal volume, positive news/price pressure can force short covering, dealer hedging, and momentum buying into the same side of the book.
- The constrained actor is the short seller or borrow-constrained participant. The expected slow variable is exchange-reported short interest, days-to-cover, borrow fee, recall pressure, and utilization; the fast trigger is catalyst surprise, mention acceleration, or abnormal price/volume.
- The intended horizon is 1d-5d after the trigger, because forced-covering pressure should appear quickly once price/borrow pressure moves against shorts. Longer horizons risk becoming a generic distress, momentum, or valuation signal.
- Negative or no-catalyst cases should not be assumed symmetric: high short interest can also identify deteriorating businesses where negative news drifts down. The test must measure whether positive shocks have larger right-tail response than negative shocks or matched non-short names.
- The generated registry coordinate `TH-db74dc5860` uses broad index ETFs (`SPY`, `QQQ`, `IWM`, `MDY`). That is likely the wrong research universe for the raw mechanism because broad ETFs usually do not provide single-name borrow-crowding/float scarcity in the same way. The mechanism belongs in `selector:research(highest_short_interest)` or an optionable high-short single-name cohort.

## Prior evidence
- **Committed Computer evidence, point-in-time 2026-06-28:** `runs/strategies/research/evidence/README.md` and `runs/strategies/research/_evidence/2026-06-28_external_evidence.md` explicitly flag this mechanism as a data gap: the committed finance snapshots do not expose a clean point-in-time short-interest or days-to-cover series. They identify possible later proxies (`finance_institutional_holders`, `finance_quotes` for shares/float, and `finance_ohlcv_histories` volume) but warn not to fabricate short interest.
- **Committed proxy data:** `runs/strategies/research/evidence/csv/*_ohlcv_90d.csv` contains daily OHLCV for NVDA, RDDT, TSLA, and SNDK from late March through 2026-06-26. Those files can identify abnormal volume and return shocks, but not whether the volume came from short covering, new longs, option hedging, index flows, or ordinary news.
- **Committed seed context:** `research/discoveries/2026-06-26_battle_scan.md` names examples such as PATH, CRM, SOUN, PLUG, HIMS, LCID, VG, MARA, and AI from an earlier Computer-captured battle scan. That note is useful as a candidate-discovery trail, not as a point-in-time SI panel or validation set.
- **Repository prior:** `research/strategy_space.py` includes `rh_high_short` as `selector:research(highest_short_interest)` and lists `short_interest_squeeze` as a candidate signal requiring structured data extraction. `runs/strategies/LADDER.md` says generated tuples carry zero weight until real research, data availability, and falsifiers are logged.
- **Evidence type classification:** current evidence is data-availability evidence plus narrative candidate discovery. It is not yet peer-reviewed or practitioner backtest evidence committed to the repo, not a cross-sectional event study, and not sufficient for `keep_for_testing`.

## Data availability without live connectors
- **Available now to sal-bot offline:**
  - `runs/strategies/research/evidence/csv/NVDA_ohlcv_90d.csv`, `runs/strategies/research/evidence/csv/RDDT_ohlcv_90d.csv`, `runs/strategies/research/evidence/csv/TSLA_ohlcv_90d.csv`, and `runs/strategies/research/evidence/csv/SNDK_ohlcv_90d.csv` for daily price/volume proxy checks.
  - `runs/sentiment/series/TICKER_*.jsonl` for the existing Computer-captured web-sentiment score/price proxy series, but these files do not carry short interest or borrow fields.
  - `research/discoveries/2026-06-26_battle_scan.md` for examples and caveats, not for testing.
- **Observed proxy summary from committed CSVs:** the four OHLCV files each have 62 rows ending 2026-06-26. Over that window SNDK shows the most squeeze-like price path (+265% close-to-close, max absolute daily return 22%, last-20-day volume z-score about +2.1), RDDT rises about +35% with a 13% max daily move, NVDA rises about +17%, and TSLA about +7%. This is descriptive only; none of it proves high SI or forced-covering.
- **Missing fields that block testing:** point-in-time short interest, exchange publication date, settlement date, shares float/free float, days-to-cover, borrow fee, utilization, lendable supply, recall/locate stress, options open interest/dealer gamma if the test claims option-hedging amplification, and tradeability/liquidity filters for Robinhood.
- **Lag and revision risks:** U.S. exchange short interest is published with delay and is not a same-day live field. Any feature must use the publication timestamp available before the decision, not the settlement date or a later revised vendor page. Borrow-fee/utilization data may be intraday and vendor-specific; if Computer cannot capture a stable historical feed with timestamps, the signal should be killed before testing.
- **Point-in-time gap:** the committed finance evidence states `finance_*` does not currently provide SI/days-to-cover as a first-class field. Therefore the signal is `needs_more_research` until Computer commits a point-in-time SI/borrow fixture or rejects the data path.

## RH-tradeable universe and proxies
- **Preferred selector before any test:** `selector:research(highest_short_interest AND rh_tradeable AND liquid)` resolving to at least 30 U.S. equities/ETFs available through Robinhood Agentic, with minimum dollar volume, price floor, and borrow/SI coverage. The four seed names are examples/data-availability probes, not breadth.
- **Why not the generated ETF coordinate:** `TH-db74dc5860` uses `rh_index_etfs` (`SPY`, `QQQ`, `IWM`, `MDY`). Index ETFs can be pair-neutral hedges or market controls, but they are weak direct subjects for single-name float-squeeze mechanics. Keep them as benchmarks/controls, not the primary high-short selector.
- **RH constraints from `CHARTER.md`:** equities and ETFs are real-order eligible; equity/index options are level-2 eligible; crypto is watch-only; no margin or naked options. This dossier does not propose an order, structure, or size.
- **Tradeable proxy if SI data remains unavailable:** abnormal dollar volume divided by estimated float can be a weak forced-cover proxy only after Computer commits point-in-time shares/float. OHLCV volume alone is too circular and should not qualify for testing.
- **Minimum breadth:** at least 30 resolved high-short, liquid, RH-tradeable names before `testing`, with no more than a small minority coming from the current four tracked battle names. The cross-sectional gate should require the asymmetry in at least 30% of that resolved universe and across time splits, not one trophy squeeze.

## Falsifiers before testing
- **Mechanism falsifier:** high-SI names do not show larger positive-shock right tails than matched low-SI names after controlling for momentum, market beta, sector, liquidity, event type, and volatility; or high SI simply predicts negative drift/distress.
- **Data falsifier:** Computer cannot provide point-in-time SI/borrow/float fields with publication timestamps and at least 30 RH-tradeable liquid names; or the only available features are current vendor pages, revised snapshots, or volume-only proxies.
- **Circularity/lookahead guard:** SI features must be lagged to their public availability date. Trigger features must exclude same-window returns and contemporaneous volume if the target is 1d-5d return. Volume may corroborate after the fact but cannot be both trigger and outcome without a pre-lagged design.
- **Null model:** beat sector/beta/volatility matched random-label and event-date permutation nulls, plus a placebo that assigns the same positive trigger to low-SI matched names.
- **Cross-sectional generalization:** at least 30% of the resolved >=30-name universe must show the expected convex positive-shock asymmetry, not just one or two famous squeezes.
- **Capacity/implementation check:** apparent edge must survive spreads, halt/gap risk, borrow-data staleness, option liquidity, hard-to-borrow discontinuities, and the fact that squeeze candidates can be extremely volatile and crowded.

## Proposed offline eval design
- **Inputs:** a future Computer-committed fixture under `runs/strategies/research/evidence/csv/` or an adjacent static directory, with one row per `(ticker, asof_decision_ts)` containing `ticker`, `rh_tradeable`, `price`, `dollar_volume_20d`, `float_shares`, `short_interest_shares`, `short_interest_settlement_date`, `short_interest_publication_ts`, `days_to_cover`, optional `borrow_fee`, optional `utilization`, optional `lendable_supply`, and immutable source/provenance fields. Existing OHLCV files can supply target returns and volume controls.
- **Transformation:** construct lagged features only after `short_interest_publication_ts`: `si_pct_float`, `delta_si_pct_float`, `days_to_cover`, `borrow_fee_z`, and `volume_to_float`. Define positive shock from pre-lagged catalyst/sentiment inputs where available, or from an explicitly separate event fixture. Missing SI/borrow fields should be excluded or encoded as missing; never forward-fill across publication gaps without an as-of rule.
- **Targets:** 1d, 3d, and 5d forward excess returns versus sector/market controls, plus right-tail metrics such as 90th-percentile return conditional on positive shock. Exclude the event/trigger window used to form the signal.
- **Benchmark/neutralization:** compare high-SI positive-shock names to matched low-SI positive-shock names and high-SI no-shock names; neutralize sector, beta, prior 20d return, realized volatility, and dollar volume.
- **Pass bar:** minimum >=30 names and enough events that no single ticker contributes more than 10% of observations; permutation p<=0.10; no circularity flag; effect present in >=30% of names; stable sign across pre-registered time/sector splits; positive expected value after conservative transaction-cost and gap assumptions.

## Kill / keep decision
- **Recommendation: `needs_more_research`, not `keep_for_testing`.** The mechanism is economically plausible, but current committed evidence lacks the core SI/borrow series needed to test it honestly.
- Current OHLCV/volume files are useful controls and weak proxy context, but volume-only squeeze detection would be price/attention circularity dressed as short-interest research.
- The four seed names are data-availability probes and cannot establish breadth; the dossier requires a >=30-name high-short selector before any test.
- The generated broad-index-ETF coordinate should not be promoted as-is because it mismatches the single-name borrow/float mechanism.
- **Required next Computer action if kept:** review whether a point-in-time SI/borrow data path is available, commit a static as-of fixture for a >=30-name RH-tradeable high-short universe, and include source timestamps/publication lags. If no such source exists, kill this signal and add a corpse lesson: "short-interest squeeze asymmetry was economically plausible but untestable without point-in-time SI/borrow data; volume-only proxies were rejected as circular."

## Risks and open questions
- **Curve-fit-by-volume:** famous squeeze examples are seductive; testing must use a pre-declared >=30-name selector, not retrospectively chosen winners.
- **Data leakage:** delayed SI publication, revised float/share counts, and current vendor pages can leak future knowledge into historical decisions.
- **Circularity:** abnormal volume and price spikes may be the squeeze outcome, not the signal. They are not substitutes for SI/borrow pressure.
- **Source availability:** the repo currently states finance tools do not expose clean SI/days-to-cover. Borrow-fee/utilization may require a vendor Computer has not committed.
- **RH assumptions:** short-interest candidates may be low-priced, illiquid, halted, non-optionable, or unavailable; the universe must be filtered for actual RH tradeability and liquidity before testing.
- **Regime dependence:** squeeze behavior can be clustered in meme/liquidity regimes; any pass must survive out-of-sample regimes and not depend only on 2021-style anecdotes.
