# Falsification Playbook — adversarial tests we currently find useful

> Read `openness-charter.md` first. This list is a working set of useful tests, not the only ones. New falsifiers are explicitly invited.

## Stance

Each test below has been useful at least once. None is mandatory in some deep sense — they're our current best collection. We expect to add several, retire one or two that turn out to be redundant, and have the meta-orchestrator catch failure modes that motivate new tests.

When you spot a thesis that *would have* passed our current playbook but is clearly wrong on independent grounds, that's a signal to add a new falsifier — log it as a friction note (`infra_factory.py log_friction "..."`) and propose it in the next PR.

## Unconditional falsifiers (one fail → KILL)

These represent failure modes the team is currently unusually committed to catching. The bar to retire one of these is high; the bar to add new ones is intentionally low.

1. **Look-ahead leak audit**: confirm every feature at time `t` uses only data published before market close of `t-1`. Specifically:
   - No "today's close" features predicting "today's return"
   - No feature using data that gets revised (FRED initial vs final, etc.)
   - No earnings-window features that use the actual earnings result as input

2. **Random-label placebo**: shuffle the target column, re-fit, re-backtest. If Sharpe > 0.3 on shuffled labels, the model is overfitting noise.

3. **Universe placebo**: substitute the asset for a structurally similar one where the thesis should NOT work. If the strategy generates equivalent alpha on the placebo, the edge is not what the thesis claims.

4. **Date-range placebo**: split sample into two non-adjacent regimes. If signs flip or Sharpe drops > 60% in one half, thesis is regime-specific or curve-fit.

5. **Feature-importance stability**: top 3 features must be the same (or in top 5) across regime halves. Otherwise signal is unstable.

## Conditional falsifiers (fail → reviewer score drops by 2)

6. **Cost stress**: re-run with 15 bps round-trip cost. Sharpe must remain > 0.3 of pre-cost Sharpe.
7. **Slippage stress**: assume entries at next-day open instead of close — Sharpe must remain > 0.5 of base.
8. **Earnings exclusion**: drop earnings ±1 day. If >70% of return came from earnings days, reframe as post-earnings drift.
9. **Survivorship audit**: confirm universe is point-in-time correct.
10. **Macro regime overlay**: re-run conditioning on VIX > 25 vs VIX < 15. Must remain positive in both, OR thesis must claim regime dependence explicitly.
11. **Sample-size flag**: any conclusion from < 30 events triggers a small-n flag — cannot MERGE on a small-n leg without independent confirmation.

## Process falsifiers (fail → ITERATE)

12. **Fresh-reviewer test**: a new subagent with no prior context must reach the same conclusion.
13. **Adversarial PM**: reviewer must articulate the strongest steelman counter-thesis and explain why evidence beats it.
14. **One-liner test**: thesis must compress to one sentence with concrete numbers.

## Falsifiers we're considering adding (open invitation)

- **Multiple-testing correction visibility**: surface the BH-corrected p-value in every PR, not just at MERGE
- **Holdout vault validation**: explicit pre-MERGE replay against the year's reserved slice
- **Concentration test**: if >50% of returns come from <5% of days, flag as "jackpot strategy"
- **Borrow-availability check**: for shorts, confirm the name was actually borrowable on signal days
- **Vendor-data-revision audit**: for fundamental signals, confirm we use as-reported not as-restated
- **Critic-agent divergence**: an adversarial critic agent's score must be within 2 of the primary reviewer's

If any of these become routinely useful, promote them into the main lists above and log the change in a Harness PR.

## Documentation requirements

Every PR must record:
- Which falsifiers were run (paste output, not just claims)
- Which were skipped and why
- Any failures and how the iteration addressed them
- Suggestions for new falsifiers that this thesis surfaced

---

## Open questions

- Are the unconditional/conditional/process tiers well-calibrated, or should "feature-importance stability" be conditional rather than unconditional?
- Should the random-label placebo n=200 be standardized?
- The 15 bps cost-stress number is from common practice — is it right for our typical horizon?
- How do we encode falsifiers for non-equity universes (prediction markets, crypto, options) that may not have natural placebos?
- What's the falsifier equivalent for infra changes (e.g. "did this new script handle the edge case the old one missed")?
