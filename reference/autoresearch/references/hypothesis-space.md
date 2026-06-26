# Hypothesis Space

The autoresearch system does NOT depend on calendar catalysts. Catalysts are one event type within a much broader hypothesis space that is continuously, adaptively explored.

## The Grammar

Every thesis is a tuple drawn from this grammar:

```
THESIS := (SIGNAL, UNIVERSE, HORIZON, STRUCTURE, RISK)
```

### SIGNAL (the predictor)
Drawn from the alt-data + conventional-data registry. Combinable as features:

**Conventional**
- price/volume z-scores, ATR, RSI, MFI
- realized vol, vol-of-vol, vol-term-structure (VIX/VIX3M/VVIX)
- cross-asset spreads (HYG/IEF, TLT/IEI, DXY, oil-gold, copper-gold)
- factor exposures (mom, val, qual, low-vol, size, profitability)
- breadth (advance-decline, % above 200dma, McClellan)
- options surface (skew, term structure, put/call, gamma exposure)
- fundamental: earnings revisions, surprise %, accruals, FCF yield, ROIC trend
- macro: yield curve shape, real yields, financial conditions index, EPU

**Alt data**
- web search trends (Google Trends multi-keyword baskets)
- social: Reddit/X mention velocity, sentiment classification, ApeWisdom rank
- analyst behavior: estimate dispersion, revision breadth, target-price changes
- news flow: novelty score, sentiment, entity co-occurrence
- options flow: dark-pool prints, unusual options activity, dealer-positioning proxies
- on-chain (for crypto-adjacent names): exchange flows, MVRV, funding rates
- credit: CDS spreads, IG/HY OAS, primary-issuance breadth
- consumer alt: card-transaction proxies, app-store rankings (where free), search-share

**Cross-asset / regime gates**
- macro regime indicators (4-quadrant growth/inflation, recession-prob)
- volatility regime (calm/transition/stressed by realized vol percentile)
- correlation regime (single-name → index dispersion)

### UNIVERSE (the asset basket)
- single name (any liquid US equity)
- sector ETFs (XLK, XLF, XLE, XLU, XLV, XLY, XLI, XLB, XLP, XLRE, XLC)
- factor ETFs (MTUM, QUAL, VLUE, USMV, SPLV, SIZE, COWZ)
- index ETFs (SPY, QQQ, IWM, MDY, EFA, EEM, FXI)
- fixed income (TLT, IEI, HYG, LQD, EMB)
- commodities (GLD, SLV, USO, UNG, CPER, DBC)
- crypto (BTC, ETH, SOL, COIN, MSTR)
- thematic baskets (memory, power, hyperscaler, defense, GLP-1, agentic-AI)
- cross-sectional cohorts (top-decile mom / bottom-decile, etc.)
- prediction markets (Kalshi contracts on macro/weather/political)

### HORIZON
- intraday (open-to-close)
- 1-day, 3-day, 5-day
- 1-week to 1-month
- 1-3 month swing
- event-window (T-N to T+M around an event)
- regime-conditional (hold until a regime variable flips)

### STRUCTURE (how positions are formed)
- long-only (single)
- short-only (single)
- pair (long A / short B beta-neutral)
- spread (long basket / short basket)
- ranked decile (long top / short bottom from sort on signal)
- regime-overlay (apply structure only inside a regime)
- catalyst-conditional (apply structure only in event window)
- options structure (call/put/spread/condor — only if options data licensed)

### RISK (sizing + stops)
- equal-weight
- vol-target (size 1/realized-vol)
- Kelly-fraction (capped, requires positive expectancy estimate)
- equal-risk-contribution (across legs)
- hard stop / trailing stop / time stop

## The Search Process (not catalyst-driven)

The system explores this space continuously via **multi-armed bandit with Thompson sampling** over:

- **Signal arms**: which feature families are currently producing surviving theses
- **Universe arms**: which universes are showing alpha
- **Horizon arms**: which holding periods are producing edge
- **Structure arms**: which trade structures are working

Each "arm-pull" is a `(SIGNAL, UNIVERSE, HORIZON, STRUCTURE, RISK)` tuple drawn from the joint distribution, then back-tested through the full falsification pipeline. Wins narrow the prior (exploit); ties widen it (explore).

This is NOT a fixed schedule. The explorer pulls arms as fast as the action-budget permits — every cron tick is one arm-pull, plus opportunistic deep-dives on theses that survived prior pulls.

## Generators vs. Curated Seeds

Three sources feed the hypothesis space:

1. **Generated** (the bulk): the explorer samples from the grammar autonomously. Bias toward novelty (high posterior variance) plus exploitation of currently-surviving feature families.
2. **Replicated** (academic / public): take a published anomaly (PEAD, low-vol, momentum, accruals, intangibles) and reproduce in our framework with our falsifiers.
3. **Curated** (user-flagged): user can drop a thesis seed into `runs/USER_SEEDS/` and it gets fast-tracked to the front of the queue.

## Cross-Sectional Generalization Requirement

A thesis cannot MERGE on a single name. Once a single-name hypothesis survives, the **same structure must be tested on the full applicable universe** (e.g. all S&P 500 names if it's a single-name pattern, all sector ETFs if cross-sectional). The MERGE bar requires the pattern to generalize to ≥ 30% of the universe with consistent sign and at least sqrt(N) significance after multiple-testing correction.

This is the single biggest defense against the curve-fit problem. A pattern that only works on RDDT is suspect; the same pattern on 8 of 12 social/retail names is real.

## Multiple-Testing Discipline

Every hypothesis the system tests is counted in `evals/htest_log.csv`. Surviving theses get **Benjamini-Hochberg-corrected** at the family-wise level:

- The "family" is defined as one calendar week of testing
- Each thesis's p-value (from random-label placebo) is recorded
- BH correction is applied; the corrected p-value must be ≤ 0.05 to clear MERGE Gate 2
- An additional global FDR control: across the system's lifetime, the count of "surviving but unconfirmed by holdout" is tracked and capped

## Holdout Vault

A vault (`evals/holdout/`) reserves 30% of universe × time that **no exploration can touch**. Only at MERGE time, with one shot, a thesis is validated on the vault. If it fails, MERGE is blocked permanently for that exact (SIGNAL, UNIVERSE, HORIZON) configuration. The vault refreshes annually with a new random 30% draw — fixed for the year.

## Search Frontier

The system maintains a "frontier" — the current set of (signal-family, universe, horizon, structure) tuples that have produced surviving theses. The frontier is what the meta-orchestrator most cares about: when the frontier expands (new feature family produces edge), that's growth. When it contracts (theses on existing frontier start dying), that's regime-change and the meta-orchestrator should propose a new exploration boost.

## Files

- `data/registry.json` — full catalog of conventional + alt data sources with fetch-fn pointers
- `scripts/hypothesis_space.py` — grammar enumerator + Thompson sampler
- `scripts/explorer.py` — runs one bandit pull = one hypothesis test
- `scripts/cross_sectional.py` — cross-sectional generalization tester
- `scripts/multiple_testing.py` — BH correction + family tracking
- `scripts/holdout_vault.py` — vault manager + final validation
- `evals/htest_log.csv` — every hypothesis tested, with p-value and outcome
- `evals/frontier.json` — current surviving feature×universe×horizon×structure tuples
