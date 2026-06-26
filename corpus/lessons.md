# Computer Fund Lessons

Durable lessons distilled from killed theses, negative diagnostics, and review findings.
This is the seeder-facing companion to `runs/CORPSES.md`: CORPSES records what died;
this file records what future research should remember before proposing nearby variants.

This file is offline/propose-only. It must not touch Robinhood, live market data,
broker/account/order state, ARMED handoffs, sizing, or trading behavior. Lessons may
reference observed historical data only when provenance is explicit; deterministic
fixtures, simulations, and review notes must stay labeled as such.

## Discipline

When a corpse produces a reusable rule, add a lesson with these required fields:

- **Source corpse**: the `runs/CORPSES.md` entry or other offline artifact that produced the lesson.
- **Reusable lesson**: the general principle, not just a restatement of one failed thesis.
- **Seeder rule**: what future thesis-seeding prompts should prefer, avoid, or require.
- **Meta/eval linkage**: how the lesson should appear in offline review, especially the
  `memory_lessons` axis in `evals/meta_orchestrator.md` or a named deterministic eval.
- **Revisit trigger**: the exact new evidence that should cause the Fund to reconsider the lesson.

## Lessons

### 2026-06-26 — Narrative complexity must earn fidelity

- **Source corpse**: `runs/CORPSES.md` entry "Persistent-network / influencer-cascade simulator variants".
- **Reusable lesson**: realistic-looking sentiment diffusion mechanics are not automatically better;
  simulator changes must improve a named fidelity, lead-lag, or calibration metric.
- **Seeder rule**: future simulator seeds should not propose persistent network state or influencer
  cascades as standalone upgrades. They must name the missing fidelity target and the offline eval
  expected to improve before implementation.
- **Meta/eval linkage**: weekly meta passes should score repeated attempts to reintroduce these variants
  without new evidence as a `memory_lessons` regression; relevant evidence is this file plus
  `runs/CORPSES.md`.
- **Revisit trigger**: observed sentiment trajectory fixtures show a concrete lead-lag or calibration
  failure that the baseline resampled-network simulator cannot represent.

## Entry Template

Copy this block for each future distilled lesson.

```markdown
### YYYY-MM-DD — Short lesson name

- **Source corpse**: Link to `runs/CORPSES.md` entry or other offline artifact.
- **Reusable lesson**: General principle.
- **Seeder rule**: How future thesis prompts should change.
- **Meta/eval linkage**: `memory_lessons` evidence and/or named deterministic eval.
- **Revisit trigger**: Exact new evidence required before changing the lesson.
```
