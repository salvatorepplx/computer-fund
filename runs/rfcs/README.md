# Computer Fund RFCs

RFCs are lightweight, versioned design records for changes that alter the Fund's architecture,
eval discipline, data contracts, or agent boundaries. Keep them informal but falsifiable: a good RFC
states the problem, the options considered, the decision, and the evidence that would prove the
decision wrong.

RFCs are propose-only artifacts. They must not call live connectors, touch Robinhood, size orders,
route orders, or weaken the Charter rails. Designs that need live data should specify what Computer
must fetch and commit back for offline review.

## When to write one

- A change creates or revises a cross-module contract, schema, or repository state machine.
- A new data source, eval, or model materially changes the Fund's sentiment-alpha loop.
- The decision depends on explicit tradeoffs that future agents should not rediscover from scratch.
- The work spans Computer-owned connector/execution concerns and Teammate-owned offline design/evals.

## Template

```md
# RFC-NNN: Title

- Status: Proposed | Accepted | Superseded
- Owner: Teammate | Computer | Shared
- Created: YYYY-MM-DD
- Related Beads: `teammate-...`
- Scope Boundary: what this RFC explicitly does not implement or authorize

## Problem

What is broken, risky, or missing? Why does it matter to the Fund's mission?

## Context and Constraints

What repo contracts, Charter rails, connector boundaries, and existing evals shape the design?

## Options Considered

1. Option A — benefits, costs, and failure modes.
2. Option B — benefits, costs, and failure modes.
3. Option C — benefits, costs, and failure modes.

## Decision

The proposed path and why it is the smallest useful next step.

## Design

Interfaces, schemas, file paths, ownership boundaries, and integration points.

## Implementation Sequence

Small PR-sized steps, including validation for each step.

## Falsifiable Success Criteria

Observable checks that must pass, plus conditions that would force rollback or redesign.

## Open Questions

Questions that should not block the next smallest safe step.
```
