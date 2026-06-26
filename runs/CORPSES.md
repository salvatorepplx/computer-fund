# Computer Fund Corpses

Durable log for killed theses, negative diagnostics, and lessons that should feed future
research and simulation seeding. A corpse is valuable because it prevents the Fund from
rediscovering the same bad idea with a new name.

This file is offline/propose-only. It must not touch Robinhood, live market data,
broker/account/order state, ARMED handoffs, sizing, or trading behavior. Do not record
unobserved market outcomes as facts; label deterministic fixtures, simulations, review
notes, and future observed data separately.

## Discipline

When a thesis is killed, add an entry before moving on:

- **Thesis**: the claim that was tested, in one sentence.
- **Status**: `KILLED`, `REJECTED_BEFORE_TEST`, or `SUPERSEDED`.
- **Evidence type**: deterministic fixture, offline simulation diagnostic, code review,
  paper result, or observed historical data. Never blur simulated and observed data.
- **Kill reason**: the falsifier, diagnostic, constraint, or review finding that killed it.
- **Lesson**: the reusable principle to feed back into the seeder.
- **Seeder feedback**: what future research prompts, sim scenarios, or evals should prefer
  or avoid because of this corpse.
- **Reopen criteria**: the exact new evidence required before the thesis can be retried.

## Seeder Feedback Rules

- Prefer theses that explain why a prior corpse failed before proposing a nearby variant.
- Seed sims with corpse cases as adversarial controls, not as success examples.
- Promote falsifiers that killed multiple corpses into `evals/falsification_playbook.md`.
- Treat negative sim-fidelity diagnostics as research constraints until calibrated against
  observed sentiment trajectories.

## Corpses

### 2026-06-26 — Persistent-network / influencer-cascade simulator variants

- **Status**: `KILLED` as improvement candidates for SIM-FIDELITY-1.
- **Evidence type**: offline deterministic sim-fidelity diagnostic plus PR review note;
  this is not an observed market/live trading result.
- **Thesis**: making the sentiment simulator network persistent, or adding an influencer
  cascade multiplier on top of that persistent network, would improve simulator fidelity
  versus the baseline resampled-network fixture.
- **Kill reason**: PR 4 review called out that the persistent-network and
  influencer-cascade variants underperformed the baseline edge in the SIM-FIDELITY
  diagnostics and should be logged as a corpse rather than buried.
- **Lesson**: more realistic-looking diffusion mechanics are not automatically better;
  simulator changes must improve a fidelity metric instead of adding narrative complexity.
- **Seeder feedback**: future simulator-seeding prompts should not re-propose persistent
  network state or influencer cascades as standalone upgrades. They must first identify a
  missing fidelity target, with sentiment lead-lag now the key metric after the placebo
  coverage landed in PR 6 / PR 9.
- **Reopen criteria**: only retry if observed sentiment trajectory data shows a concrete
  lead-lag or calibration failure that the baseline resampled-network simulator cannot
  represent, and the proposed variant pre-registers the eval it should improve.

## Entry Template

Copy this block for each future killed thesis.

```markdown
### YYYY-MM-DD — Short thesis name

- **Status**: `KILLED` / `REJECTED_BEFORE_TEST` / `SUPERSEDED`.
- **Evidence type**: deterministic fixture / offline simulation diagnostic / code review /
  paper result / observed historical data. State whether this is simulated or observed.
- **Thesis**: One sentence claim.
- **Kill reason**: Specific falsifier, diagnostic, constraint, or review finding.
- **Lesson**: Reusable principle.
- **Seeder feedback**: How future research/sim prompts should change.
- **Reopen criteria**: Exact new evidence required before retrying.
```
