# Conviction Bar — current working thresholds

> Read `openness-charter.md` first. These thresholds are a current working hypothesis, not a rule. They should be renewed whenever calibration data argues for it.

## Stance

The numbers below represent the team's best current guess about what should gate a thesis between SEEDED → ARMED → MERGED → DEPLOYED. They are explicitly open to revision via Harness PR as we accumulate reviewer↔P&L calibration data.

We expect these thresholds to change at least once per quarter. A version that doesn't change for six months is probably under-calibrated, not perfect.

## Three gates (current working version)

### Gate 1 — ARMED (paper-trade opens)
We currently think: reviewer score ≥ **6/10** is sufficient to open a paper position.

Required at this gate:
- Hypothesis is falsifiable and pre-registered
- At least one backtest leaf shows positive expectancy out-of-sample
- No unconditional falsifier hit (see `falsification-playbook.md`)
- For grammar-sampled hypotheses: also log the raw p-value via `scripts/multiple_testing.py`

### Gate 2 — MERGED (capital-deployable)
We currently believe a thesis should clear all of:
- Reviewer score ≥ **8/10** from a fresh-context reviewer subagent
- Paper-trade live track record: ≥ **20 trading days** armed, Sharpe ≥ **0.5**, max DD ≤ benchmark DD
- Walk-forward OOS Sharpe ≥ **1.0** on the surviving tree leaf
- Information Coefficient (IC) ≥ **0.05** on OOS
- Hit rate × avg-win / avg-loss > 1 (positive expectancy enforced)
- Capacity estimate: ≥ **$1M notional** without > 10 bps slippage
- All falsifiers from the current playbook ran without unconditional hits
- **Cross-sectional generalization**: same structure tested on the broader universe, ≥ 30% of names show the pattern with consistent sign
- **Multiple-testing-corrected p-value** ≤ 0.05 (BH at family-week level)
- **Holdout vault**: one-shot validation on the year's reserved 30% slice passes
- Reviewer cannot articulate a structural reason it shouldn't work

### Gate 3 — DEPLOYED (real capital)
Always requires explicit user approval via `confirm_action`. The system drafts the trade ticket; the user authorizes execution.

## Risk caps (current working version)

- Single-thesis paper notional: ≤ 20% of paper book
- Single-name paper exposure: ≤ 15% of paper book
- Max drawdown kill switch: -15% on the thesis → auto KILL PR
- IC-decay kill switch: 20-day rolling IC drops > 50% from in-sample → auto KILL PR

## Anti-Goodhart guardrails (these we are unusually committed to)

These are not technically immutable, but the bar to change them is higher than the rest:

- Sharpe alone never triggers MERGE — must combine with reviewer + paper track record + cross-sectional generalization + holdout pass
- Reject any backtest that requires > 3 hyperparameters tuned post-hoc
- Reject any thesis whose edge disappears under any single falsification test
- Reject any thesis whose top feature is suspected of look-ahead leakage until proven otherwise
- Never relax capability-eval targets downward to make pass rates look healthier

## Provenance

Initial thresholds set 2026-05-18 based on judgement, not calibration data. Once we have ≥10 closed paper positions, the calibration tracker should be the primary input to any threshold revision.

---

## Open questions

- Are the numeric thresholds (Sharpe ≥ 1.0, IC ≥ 0.05) the right ones, or did we pick "round-ish" values?
- The cross-sectional generalization rule (≥30% of names) is a guess — should it be a function of universe size?
- Should reviewer ≥ 8/10 be sample-size-dependent? An 8/10 with n=200 OOS days is much stronger than an 8/10 with n=20.
- Is one-shot holdout validation the right discipline, or should it be a held-out *every-N-iterations* check?
- Should there be a Gate 1.5 between ARMED and MERGED for "promoted but not full size"?
- What's the equivalent of these thresholds for infra (scripts, evals) rather than theses?
