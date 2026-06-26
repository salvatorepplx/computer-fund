# Computer Fund Sentiment Falsification Playbook

This playbook is offline/propose-only. It defines falsifiers for sentiment-alpha hypotheses before any thesis can be considered for autonomous execution by Computer under the repository safety rails. It must not touch Robinhood, broker connectors, live market data, account/order state, order placement, or ARMED recommendations.

All examples and starter evals use deterministic simulated fixtures unless explicitly labeled as future observed data.

## Tier 0: Integrity REG Evals

These checks must stay at 100% because they guard against fake or unsafe research plumbing.

- **No look-ahead leak audit**: every feature timestamp must be at or before the decision timestamp; future sentiment, realized price, or post-fill information is unavailable to the signal.
- **Observed/simulated boundary**: simulated sentiment projections must be labeled as projections and must not overwrite observed sentiment records.
- **Execution isolation**: eval code must remain connector-free and must not read broker/account/order state.
- **Determinism**: fixture evals must produce identical output for identical inputs and seeds.

## Tier 1: Placebo Falsifiers

These falsifiers try to kill the hypothesis before cost or sizing discussions.

- **Random-label placebo**: shuffle or otherwise scramble sentiment labels. A surviving edge means the pipeline is fitting noise or leaking future information.
- **Universe placebo**: run the signal against an unrelated battle/name where the mechanism should not apply. A surviving edge means the universe definition is too loose.
- **Sentiment lead-lag placebo**: require projected sentiment to lead a later observed sentiment/price proxy. Coincident, lagging, random-label, and wrong-universe controls must be rejected.
- **Direction placebo**: invert the sentiment direction. A bullish edge that also works when inverted is not a directional sentiment edge.

The first implemented fixture-level check is `python -m evals.leadlag_placebo`, which accepts a true leading synthetic signal and rejects coincident, lagging, random-label, and wrong-universe controls.

## Tier 2: Robustness Splits

These checks become mandatory once real observed history exists.

- **Date/regime split**: evaluate separately by market regime, event density, and sentiment venue mix; do not average away a regime-specific failure.
- **Holdout discipline**: freeze acceptance criteria before looking at a new holdout period.
- **Ticker/battle split**: verify that one contested location or one high-volatility name is not carrying the full result.

## Tier 3: Tradability Stress

These checks measure whether a surviving sentiment edge can survive Computer Fund’s small-book constraints.

- **Cost/slippage stress**: re-score edge after spread, fees, and conservative fill assumptions. A few cents can erase a meaningful fraction of a $1k-book edge.
- **Latency stress**: shift entry later by one or more heartbeat intervals; a signal that only works with impossible timing is rejected.
- **Sizing-cap stress**: evaluate under current Charter caps rather than idealized notional exposure.

## Promotion Rule

A sentiment thesis is not promoted by raw edge magnitude alone. It must first survive Tier 0 integrity checks, then Tier 1 placebo falsifiers, with sentiment lead-lag as the key fidelity metric: projected sentiment must predate the observed proxy rather than coincide with or lag it.
