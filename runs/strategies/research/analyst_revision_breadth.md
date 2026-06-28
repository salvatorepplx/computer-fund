# analyst_revision_breadth researched-rung dossier

- **Status:** draft
- **Recommendation:** needs_more_research
- **Signal family:** analyst_revision_breadth
- **Candidate coordinates:** `TH-b4dcf23284` (`rh_thematic`, 5d, `regime_overlay`, `kelly_capped`); `TH-75144af2b1` (`rh_all_liquid`, 1d, `long_short_single`, `equal_weight`); `TH-61d65c31c9` (`battle_singles_seed`, 5d, `ranked_decile`, `equal_weight`); `TH-c3f14dbaa5` (`rh_all_liquid`, 3d, `long_short_single`, `kelly_capped`)
- **Author / date:** dossier-analyst_revision_breadth-fded, 2026-06-28
- **Boundary:** offline/propose-only; no live connectors, Robinhood calls, capture, sizing, `runs/PROPOSED/`, ARMED handoff, registry mutation, or observed-series mutation

## One-line thesis

If multiple analysts independently revise targets/ratings/earnings estimates in the same direction after a catalyst, the revision diffusion and post-earnings drift should predict 3d-20d abnormal returns before the full institution-following crowd incorporates the information.

## Mechanism

- Analyst revisions are slow-moving, dated events: firms update models after earnings, guidance, conferences, or channel checks; the signal is the breadth and direction of those dated updates, not the current consensus level.
- PEAD-style underreaction is the economic story: market participants may incorporate the announcement-day surprise immediately but underweight follow-on estimate/target diffusion and delayed institutional model updates over subsequent days or weeks.
- The plausible horizon is 3d-20d after the revision/earnings event. Same-day or 1d moves are explicitly not sufficient because the committed seed evidence says 1d post-earnings moves are noisy and sign-inconsistent.
- This is not a pure sentiment signal. It only becomes investable if point-in-time analyst rows can be lagged to first availability and shown to add information beyond price momentum, earnings surprise, announcement-day return, and sector moves.

## Prior evidence

- **Repo contract / prior taxonomy:** `runs/strategies/research/README.md` names analyst-revision breadth / PEAD as delayed institutional incorporation of estimate and rating revisions, likely at 3d-20d horizons, but requires timestamp and lag handling before testing.
- **Computer-captured point-in-time evidence:** `runs/strategies/research/_evidence/2026-06-28_external_evidence.md` records a static 2026-06-28T00:55Z Perplexity Finance snapshot captured by Computer, not sal-bot. It includes analyst consensus/price-target rows and earnings-history rows for NVDA, RDDT, TSLA, and SNDK.
- **Committed per-name CSV probe:** `runs/strategies/research/evidence/csv/*_analyst_targets.csv` contains dated rows with `rating_current`, `rating_prior`, `price_target_current`, `price_target_prior`, `action`, and `sentiment`; `*_earnings_history.csv` contains `actualEps`, `estimatedEps`, `epsSurprise`, `postEarningsMoveOneDay`, and expected move fields.
- **Observed seed examples:** in the committed CSVs, NVDA has 26 up / 0 down / 13 unchanged target revisions across 39 rows; SNDK has 36 up / 0 down / 0 unchanged across 36 rows; RDDT has mixed revisions (16 up / 12 down / 9 unchanged); TSLA has high disagreement (10 up / 10 down / 17 unchanged plus bull/neutral/bear mix). These show feature availability, not edge.
- **Insufficient source standard:** no independently sourced academic/practitioner literature files for PEAD or analyst revisions were committed with this task. Because the dossier contract requires at least 3 independent sources for any `keep_for_testing` recommendation, this dossier cannot honestly recommend `keep_for_testing` from the current repo evidence alone.

## Data availability without live connectors

- Available offline now:
  - `runs/strategies/research/evidence/README.md` documents provenance, timestamp, boundary, and the 4-name seed scope.
  - `runs/strategies/research/evidence/csv/NVDA_analyst_targets.csv`, `RDDT_analyst_targets.csv`, `TSLA_analyst_targets.csv`, and `SNDK_analyst_targets.csv` provide 36-39 dated analyst target/rating rows per seed name.
  - `runs/strategies/research/evidence/csv/*_earnings_history.csv` provides about 5 historical earnings rows plus one future estimate row per seed name.
  - `runs/strategies/research/evidence/csv/*_ohlcv_90d.csv` provides 62 daily OHLCV rows per seed name for return context, but 90d OHLCV is too short for a real cross-sectional event study.
- Current limitations:
  - The universe is only NVDA, RDDT, TSLA, and SNDK; it is an availability probe and cannot satisfy cross-sectional breadth.
  - The target rows have analyst event dates but not a separately verified first-publication timestamp, provider ingestion timestamp, or market-close availability cutoff.
  - The earnings rows include only 1d post-earnings move; PEAD requires multi-day cumulative abnormal returns after the announcement, not just the first reaction.
  - The CSVs include target/rating rows, but no point-in-time EPS-estimate revision history before each earnings event; that blocks a clean SUE/revision-breadth decomposition.
  - Survivorship and selection risk are high because the four seed names were already contested battle names, not a pre-registered liquid universe.
- Computer-only data needed later, without sal-bot calling connectors:
  - A ≥30-name RH-tradeable liquid-equity capture with the same analyst target/rating schema, preferably ≥60 names to survive missing coverage.
  - At least 1-2 years of daily OHLCV for each selected name and benchmark/sector proxies.
  - Multi-day post-event returns or enough OHLCV to compute 3d, 5d, 10d, and 20d cumulative abnormal returns after each analyst/earnings event.
  - Point-in-time analyst-estimate revisions or explicit confirmation that target/rating rows are first-observed, not restated/current-page snapshots.
  - Publication/availability lag rules: after-hours earnings should be eligible only from the next regular session, and analyst rows should be lagged until after a conservative availability cutoff.

## RH-tradeable universe and proxies

- Proposed selector for any future test: `rh_all_liquid_revision_coverage_v1`, defined as RH-tradeable US common stocks/ADRs with average dollar volume above a Computer-chosen liquidity floor, price above a penny-stock floor, at least 8 dated analyst target/rating rows in the trailing 60 days, and at least 4 historical quarterly earnings rows.
- Minimum breadth: at least 30 resolved names after coverage/liquidity filters; 60+ requested so missing analyst coverage does not collapse the test.
- Structure: rank cross-sectionally by lagged revision breadth and magnitude; compare top vs bottom deciles or long top / short bottom only in simulation. For real RH constraints, equities and long options are allowed by `CHARTER.md`, crypto is watch-only, and shorting/borrow availability is not guaranteed; therefore live implementation would likely start as long-only/top-decile or long-vs-cash until Computer proves a valid RH short/proxy path.
- Basis risk: target-price revisions may reflect sell-side consensus behavior rather than tradable order flow; options liquidity, spreads, and post-earnings volatility crush may erase any signal even if the equity event study is positive.

## Falsifiers before testing

- **Mechanism falsifier:** if revision breadth is strongest only after the price has already moved, and lagged revision breadth adds no predictive power after controlling for 5d/20d momentum, earnings surprise, announcement-day return, and sector return, the mechanism is price-following commentary rather than delayed incorporation.
- **Data falsifier:** kill the signal if Computer cannot provide first-observed, point-in-time analyst revision rows or a conservative lag that prevents current-page/restated analyst data from leaking into historical decisions.
- **Circularity/lookahead guard:** construct features only from rows whose event date and availability timestamp are before the decision timestamp; exclude analyst summaries that include post-event price moves; lag after-hours events to next-session open or close; pre-register the target horizon before inspecting returns.
- **Null model:** beat random-label and date-permutation nulls where revision events are shuffled within sector/month buckets, plus a placebo using unchanged target rows.
- **Cross-sectional generalization:** require consistent-sign results on at least 30% of the resolved ≥30-name universe and avoid declaring success from NVDA/SNDK-like trophy cases.
- **Capacity/implementation check:** require minimum dollar volume, max spread/slippage assumptions, earnings blackout handling, and a version that does not depend on unavailable borrowing or illiquid options.

## Proposed offline eval design

- Inputs:
  - Current seed fixture: committed `*_analyst_targets.csv`, `*_earnings_history.csv`, and `*_ohlcv_90d.csv` for parser/feature smoke tests only.
  - Future Computer capture: ≥30 RH-tradeable names with analyst target/rating history, earnings history, and 1-2 years of OHLCV.
- Transformation:
  - For each `(symbol, decision_date)`, compute trailing 5d/20d revision breadth: count and fraction of analysts with upward, downward, and unchanged price-target/rating changes; median and mean target-change percentage; sentiment mix; and dispersion change.
  - Construct PEAD features separately: standardized EPS surprise, revenue surprise where available, and post-announcement revision breadth measured only after the event and before the decision date.
  - Lag every feature by one full trading session unless Computer proves an earlier timestamp is safely available.
  - Neutralize or bucket by sector and recent momentum; treat missing target priors as missing rather than zero revision.
- Targets:
  - 3d, 5d, 10d, and 20d forward cumulative abnormal returns versus SPY/QQQ and sector ETF where available.
  - Exclude the announcement-day move from the drift target; separately report whether the signal merely predicts event-day reaction.
- Pass bar before any promotion beyond research:
  - At least 30 names and at least 100 independent analyst/earnings decision events after lag filters.
  - Permutation p-value ≤0.10 before any `testing` claim and ≤0.05/BH-adjusted before any later edge claim.
  - Circularity check: revision breadth retains direction and material effect after controlling for recent price momentum and event-day return.
  - Hit-rate/generalization: consistent sign in ≥30% of the universe and not concentrated in one ticker, sector, or one earnings season.
  - Robustness: separately pass on earnings-window and non-earnings analyst-revision subsets, or explicitly narrow the signal to PEAD only.

## Kill / keep decision

- **Recommendation:** `needs_more_research`, not `keep_for_testing`.
- The mechanism is plausible and already in the repo taxonomy, but the committed evidence is a 4-name Computer-captured point-in-time probe, not a cross-sectional study.
- The seed evidence is mixed: SNDK looks like a clean upward-revision/positive-surprise case, NVDA shows upward target revisions with negative 1d post-earnings moves, and RDDT/TSLA are sign-inconsistent or disagreement-heavy.
- Current data does not establish first-publication lag, multi-day PEAD returns, or EPS-estimate revision history; those are required to avoid lookahead and price-circularity.
- Required next Computer review action if continued: capture the proposed ≥30-name `rh_all_liquid_revision_coverage_v1` panel with point-in-time analyst rows and 1-2 years of OHLCV, plus either committed literature snapshots or explicit decision to treat this as a pure data-availability research task.

## Risks and open questions

- **False breadth:** 36-39 analyst rows per seed name are not universe breadth; four names cannot prove a cross-sectional edge.
- **Selection bias:** the seed names were known battle locations, so observed revision waves may be selected after the fact.
- **Lookahead:** provider target/rating pages can be revised or backfilled; without first-observed timestamps, historical feature construction is suspect.
- **Circularity:** analysts may raise targets because price already rose or because public news already moved the stock; the signal must beat momentum and event-day controls.
- **Regime dependence:** analyst-revision effects may differ in AI/semiconductor hype regimes versus normal sectors.
- **Implementation:** RH constraints favor long-only equity or defined-risk options; any long/short decile structure needs a Computer-owned proof that both legs are executable under `CHARTER.md` rails.
