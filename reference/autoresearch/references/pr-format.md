# PR Format

Every iteration of a thesis is logged as a PR file at `runs/<thesis_id>/prs/PR-NNN.md`.

## Template

```markdown
# PR-NNN: <one-line title>

**Thesis ID**: <slug>
**Iteration**: NNN
**Date**: YYYY-MM-DD
**Status**: DRAFT | ARMED | MERGED | ITERATING | KILLED
**Parent PR**: PR-(NNN-1) | (root)

## Hypothesis (one sentence, with numbers)
On <asset>, signal <S> predicts <return R> over <horizon H>, with expected Sharpe ≥ <X> and IC ≥ <Y>.

## Diff from parent PR
- What changed since PR-(NNN-1) (feature, horizon, filter, model, universe)
- Why (open question from prior PR)

## Pre-registration
- Predicted Sharpe: 
- Predicted IC:
- Predicted hit rate:
- Predicted capacity ($ notional):
- Kill switches: drawdown >X%, IC-decay >Y%, days-since-signal >Z

## Falsifiers identified upfront
List the specific results that would force you to abandon. Bind yourself before running.

## Experiment tree
| Leaf ID | Feature | Horizon | Filter | Risk | OOS Sharpe | OOS IC | Notes |

(Mark prune ✂ vs survive ✅ for each.)

## Falsification suite results
Pull from falsification-playbook.md and record pass/fail per test.

## Reviewer verdict
- Reviewer subagent ID:
- Score (0-10):
- Steelman counter-thesis:
- Recommendation: ARM | ITERATE | KILL

## Paper-trade actions
- Opened: ticker, side, size, entry px, stop, target
- Closed:
- Live P&L since PR:

## What would change my mind (open questions)
- Each open question becomes a candidate seed for the next iteration.

## Decision
**MERGE / ITERATE / KILL** — and why in one paragraph.
```

## Hard rules
- Iteration N+1 must explicitly address at least one open question from iteration N.
- Killed PRs never get revived without new external evidence (new data source, new market regime).
- ARMED status writes immediately to the paper book — do not delay.
