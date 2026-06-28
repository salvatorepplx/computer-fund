# STRAT-WIDE researched-rung dossiers

This directory is the sal-bot/Teammate contract for turning broad strategy coordinates into
`researched`-rung dossiers. It is deliberately docs-only and propose-only: dossiers can recommend
`keep_for_testing` or `kill`, but they do not change registry status, start live capture, touch
Robinhood, write `runs/PROPOSED/`, or promote anything to `testing`. Computer owns live connector
calls, observed strategy state, and any promotion after review.

The ladder in `runs/strategies/LADDER.md` is binding: generated tuples carry zero weight until an
independent mechanism survives real research, data-availability checks, and explicit falsifiers.

## Dossier template

Each signal investigation should write one file at `runs/strategies/research/<signal>.md` using this
shape. Keep the file compact enough to review, but specific enough that a second worker can falsify it.

```md
# <signal> researched-rung dossier

- **Status:** draft | ready_for_computer_review | killed_before_testing
- **Recommendation:** keep_for_testing | kill | needs_more_research
- **Signal family:** <strategy_space.py signal name or new proposed family>
- **Candidate coordinates:** <registry ids if applicable; otherwise proposed tuple coordinates>
- **Author / date:** <teammate worker slug>, YYYY-MM-DD
- **Boundary:** offline/propose-only; no live connectors, Robinhood calls, capture, sizing, or ARMED handoff

## One-line thesis
State the mechanism in one falsifiable sentence.

## Mechanism
- Why should this signal predict future returns instead of merely describe current price?
- Who is slow, constrained, overreacting, underreacting, hedging, forced to cover, or forced to rebalance?
- What horizon should the mechanism operate on, and why is that horizon not arbitrary?

## Prior evidence
- Summarize at least 3 credible sources, with links/citations captured in the dossier.
- Separate peer-reviewed/practitioner evidence, vendor/blog claims, and anecdotal examples.
- Record whether evidence is cross-sectional, time-series, event-study, or narrative-only.

## Data availability without live connectors
- List offline sources sal-bot can inspect now: committed repo fixtures/series, public static files,
  local docs, package documentation, previously committed raw snapshots, or synthetic fixtures.
- List connector/live sources Computer would need later, without calling them.
- Identify timestamp fields, publication lag, revision lag, survivorship risk, and point-in-time gaps.
- Mark the signal `kill` if no plausible point-in-time data path exists.

## RH-tradeable universe and proxies
- Define the intended Robinhood-tradeable universe as a selector, not a hand-picked trophy list.
- Note equity/ETF/options/crypto-watch-only constraints from `CHARTER.md`.
- If the raw signal is not directly tradeable, define the proposed RH proxy and basis risk.
- State expected minimum breadth before testing; default is at least 30 liquid names unless the dossier
  argues for a narrower, structurally coherent universe.

## Falsifiers before testing
- **Mechanism falsifier:** what observation would make the story economically implausible?
- **Data falsifier:** what missing/lagged/revised field kills the signal?
- **Circularity/lookahead guard:** how to prove the signal is not price-in-disguise or future leakage?
- **Null model:** what permutation/placebo/random-label test must it beat?
- **Cross-sectional generalization:** what fraction of the universe must show the effect?
- **Capacity/implementation check:** why should spreads, borrow, option liquidity, or event timing not erase it?

## Proposed offline eval design
- Inputs: exact files/fixtures or proposed fixture schema.
- Transformation: point-in-time feature construction, normalization, lag, and missing-data handling.
- Targets: return horizon(s), benchmark/neutralization, and leakage exclusions.
- Pass bar: minimum N, permutation p-value, circularity threshold, universe hit-rate, and robustness splits.

## Kill / keep decision
- Recommendation with 3-5 bullets of evidence.
- Required next Computer action if kept, phrased as a review request rather than an execution request.
- Corpse lesson to add if killed.

## Risks and open questions
- List unresolved risks, especially curve-fit-by-volume, circularity, data leakage, source availability,
  RH universe assumptions, and regime dependence.
```

## Evidence standards

- Use a minimum of 3 independent sources for any `keep_for_testing` recommendation; at least one should
  be academic, regulatory/exchange, or a reputable practitioner paper when available.
- Capture exact source URLs, publication dates, and the claim each source supports. Do not cite sources
  for broad vibes.
- Distinguish mechanism evidence from backtest evidence. A backtest without mechanism is not enough;
  a mechanism without point-in-time data is not enough.
- Prefer negative evidence and failed replications over promotional strategy writeups. If evidence is
  vendor-only or anecdotal, default to `needs_more_research` or `kill`.
- Require point-in-time reasoning for every field. If a field is revised, restated, delayed, scraped from
  a current page, or selected after the outcome, treat it as suspect until proven otherwise.

## Offline-only data checks

Sal-bot workers may do these checks without crossing the live boundary:

- Inspect `research/strategy_space.py` for existing signal names, selectors, horizons, structures, and
  risk modes; propose new coordinates only as prose, not registry mutations.
- Inspect `runs/strategies/REGISTRY.json` and `runs/strategies/LADDER.md` to map candidate coordinates
  and required rung gates; do not edit statuses.
- Inspect committed sanitized series or fixtures under `runs/sentiment/` only as historical artifacts;
  do not run capture, mutate series, or infer live readiness from small-N data.
- Write synthetic fixtures that model lag, missingness, circularity, and source disagreement when an
  eval needs a regression guard.
- Use public documentation or static downloaded files only when the source is accessible without account,
  trading, broker, or live market-data connectors.
- Record any Computer-only data requirements explicitly, including why live review is needed and what
  failure should cause Computer to reject promotion.

## Falsifier defaults

A dossier can tighten these, but should not weaken them without explaining why.

- **Minimum N:** no testing promotion on tiny examples; match or exceed the relevant harness floor.
- **Permutation null:** require statistical evidence against random labels before any `edge` claim.
- **Circularity guard:** kill features that contemporaneously track price levels or include price-derived
  fields while claiming to be independent sentiment/fundamental signals.
- **Cross-sectional generalization:** require the effect across at least 30% of the resolved universe, not
  one lucky name.
- **Forward/holdout split:** separate source discovery from later evaluation when historical data exists.
- **Cost/implementation sanity:** reject signals whose apparent edge depends on untradeable names, stale
  quotes, unavailable borrow, illiquid options, impossible timestamps, or post-close data used pre-close.

## Worker fanout shape

Use one independent worker per signal packet, plus one critic pass across all completed dossiers.

1. **Signal worker:** owns exactly one signal family and writes one dossier. It should be skeptical,
   source-grounded, and willing to kill the idea.
2. **Data worker:** optionally follows when the signal worker identifies a plausible offline fixture or
   schema; it writes synthetic/fixture eval proposals only, not live fetchers.
3. **Quant critic:** reviews the dossier for leakage, circularity, multiple-testing, universe selection,
   and false breadth.
4. **Integrator:** updates a summary table after dossiers land and recommends which, if any, Computer
   should consider for `testing`.

Do not run ten workers that all produce shallow lists. The target is independent researched mechanisms,
not volume.

## First five signal packets

Start with five packets because they are distinct mechanisms and map to the current grammar or examples
Computer named:

1. **Analyst-revision breadth / PEAD** — delayed institutional incorporation of estimate and rating
   revisions; likely horizons 3d-20d; needs point-in-time revision timestamps and lag handling.
2. **Short-interest squeeze asymmetry** — crowded shorts plus positive catalyst/mention acceleration can
   create convex upside; needs publication-lag honesty, borrow/float context, and RH proxy breadth.
3. **Mention-velocity acceleration** — change in attention volume may lead near-term flows; must avoid
   source-count circularity, price-news feedback, and one-source overfitting.
4. **Cross-source sentiment divergence** — disagreement between social, news, and search sentiment may
   predict reconciliation; requires source availability map and explicit lag/quality weighting.
5. **Vol-regime-gated reversion** — realized-volatility regimes decide whether sentiment/price extremes
   mean-revert or continue; price-only components need especially strict circularity and cost checks.

Each packet should name the likely `strategy_space.py` coordinates, but should not edit
`runs/strategies/REGISTRY.json`. If a packet proposes a new coordinate, it remains prose until Computer
accepts the shape.

## Common failure modes

- **Curve-fit-by-volume:** many generated tuples create the illusion of breadth; count only researched
  independent mechanisms.
- **Circularity:** search/news/sentiment features can smuggle price moves back into the signal.
- **Data leakage:** current web pages, revised estimates, and delayed short-interest reports can imply
  information the Fund would not have had at decision time.
- **Source availability:** a signal may depend on X/Reddit/vendor data that sal-bot or Computer does not
  actually have; kill or scope it down rather than hand-wave.
- **RH universe assumptions:** availability on Robinhood, liquidity, options level, borrow constraints,
  and crypto watch-only status can invalidate an otherwise interesting mechanism.
- **Multiple testing:** independent dossiers reduce shared bias, but promotion still needs null tests and
  holdouts because many plausible mechanisms will be noise.

## Recommended next step

Create research-worker Beads for the five packets above after this docs contract lands. The next artifacts
should be five independent dossier files under this directory, not registry promotions. Computer can then
review any `keep_for_testing` dossier and decide whether to allocate live connector work to build the
testing harness.
