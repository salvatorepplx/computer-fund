# Production / AI-Code Discipline Guide

- Status: Proposed
- Owner: Shared: Teammate proposes and reviews offline changes; Computer owns live connectors and execution
- Created: 2026-06-28
- Related Beads: `teammate-yr7.1`
- Scope Boundary: this guide does not authorize live connector use, market/account/order API calls, Robinhood access, state promotion, deployment, or mutation of generated/live state

## Purpose

Computer Fund is a money-adjacent autonomous trading system. Its worst engineering failure mode is
not merely a bug; it is AI-generated code that reaches a local goal while quietly weakening the rails
that keep capital safe. This guide defines the production discipline expected for Fund changes and the
anti-patterns reviewers should reject.

Production-grade Fund code should be small, typed, falsifiable, provenance-rich, and fail-closed. It
should make unsafe actions structurally hard or impossible. AI goal-reaching code often does the
opposite: it patches until the demo passes, fabricates missing context, treats tests as decoration,
adds broad mocks, converts uncertainty into defaults, and blurs propose-only artifacts with execution
intent. In this domain, that behavior is unacceptable.

This document is a standing review guide, not live state. Do not update it from ticks or automation.
Use RFCs under `runs/rfcs/` for versioned design decisions and use this guide as the baseline standard
for those RFCs and PRs.

## Non-Negotiable Rails

The Charter and handoff contract are higher authority than any implementation convenience.

- `CHARTER.md` is LAW: account allowlist, review-before-place, sizing ladder, kill-switch,
  bounded-downside option structures, timestamped signals, no fabrication, and post-trade logs.
- `CONSTITUTION.md` defines the improvement mandate, but improvement never self-modifies the safety
  rails away.
- `HANDOFF.md` separates roles: Teammate proposes through offline repo artifacts; Computer owns live
  connectors, market/account/order context, promotion, execution, and disclosure.
- `runs/PROPOSED/README.md` and the proposed-artifact schema separate offline proposals from any
  execution authorization. `PROPOSED` artifacts must remain incapable of placing or implying orders.
- Existing evals such as `evals/proposed_validator.py`, `evals/leadlag_permutation.py`, and
  `evals/web_sentiment_invariants.py` are examples of offline, falsifiable checks that should be
  strengthened rather than bypassed.

When implementation pressure conflicts with these rails, the correct behavior is to stop, fail closed,
and write a proposal or RFC explaining the missing contract.

## Production Code vs. AI Goal-Reaching Code

| Dimension | Production-grade Fund code | AI goal-reaching code to reject |
|---|---|---|
| Safety posture | Refuses ambiguous state, missing rails, unknown accounts, unvalidated schemas, stale inputs, and unsupported order shapes | Defaults missing values into permissive behavior so the path can continue |
| Tests | Small tests that lock high-risk contracts, invariants, and regressions | Large brittle snapshots, broad mocks, trivial coverage, or tests that only assert implementation wiring |
| Types and schemas | Typed boundaries at repo artifacts, connector seams, state transitions, and money quantities | Ad hoc dicts, stringly typed states, optional fields with hidden meanings, unvalidated JSON |
| Provenance | Every signal and proposal carries timestamped source lineage and simulation/observed labels | Summaries without raw references, fabricated values, or copied context with no origin |
| Side effects | Side effects are explicit, owner-scoped, reviewed, and impossible from offline paths | Helper functions that silently write state, hit live APIs, place orders, or promote artifacts |
| Design | Small contracts, named invariants, explicit tradeoffs, and RFCs for cross-module changes | Opportunistic glue, global flags, hidden coupling, or broad rewrites to make one task pass |
| Failure | Raises, aborts, marks invalid, or produces no artifact when safety cannot be proven | Continues with best-effort guesses in order to satisfy the immediate prompt |

## AI Code Anti-Patterns to Reject

Reject or request redesign when a PR shows any of these patterns:

1. **Goal-passing over rail-preserving.** The change makes a scenario pass by loosening Charter,
   handoff, schema, or validator checks instead of satisfying them.
2. **Permissive fallback on missing money facts.** Missing account id, buying power, quote, halt/PDT
   status, option structure, risk phase, timestamp, or provenance becomes `0`, `False`, `today`,
   `unknown`, or a default account that lets the flow continue.
3. **Execution intent leakage.** Offline code, tests, docs fixtures, `PROPOSED` artifacts, or Teammate
   owned paths include order placement, sizing instructions intended as authorization, broker review
   output, `ARMED` promotion, or live connector calls.
4. **Fabricated or unlabeled signal.** Simulated, derived, stale, or hand-entered sentiment is stored
   as observed fact, lacks `observed_at`, or loses source lineage.
5. **Stringly typed state machines.** Transitions such as `PROPOSED -> ARMED -> EXECUTED` are handled
   by loose string checks without schema validation, ownership checks, or impossible-state tests.
6. **Broad mock illusion.** Tests mock away the risky behavior being claimed safe: account selection,
   broker review, schema validation, timestamp ordering, side-effect boundaries, or connector failures.
7. **Snapshot bulk instead of invariant tests.** Tests assert huge JSON/text blobs while missing the one
   safety property that matters.
8. **Global side effects in helpers.** Import-time work, default live clients, implicit writes to
   `state/`, `runs/ARMED/`, `runs/EXECUTED/`, `runs/QUEUE.json`, or external services.
9. **Untyped money math.** Floats and untagged numbers cross boundaries without currency, instrument,
   premium/collateral semantics, book basis, or rounding rules.
10. **Design-free coupling.** A change spans execution, graph, evals, schemas, and state with no RFC,
    no stated owner boundary, and no falsifiable success criteria.
11. **Cleverness over auditability.** Metaprogramming, dynamic imports, hidden registries, or opaque
    prompt-like logic make safety review depend on reading runtime behavior rather than contracts.
12. **Green CI by deleting friction.** Removing evals, narrowing validators, muting failures, or
    marking risky tests as skipped without a replacement safety check.

## Principles to Enforce

### 1. Fail Closed by Default

Ambiguity must stop the flow. For money-domain code, the safe default is not "best effort"; it is
"no proposal, no promotion, no order, no state mutation."

Require fail-closed behavior for:

- account allowlist mismatches or absent account ids;
- missing or stale market/account/order review data;
- unknown instrument type, unsupported option structure, or untagged buying-power basis;
- schema parse failures, unknown artifact state, impossible owner/writer combinations, or extra fields
  that could imply execution intent;
- missing timestamps, mixed timezone assumptions, or out-of-order observed series;
- connector failure, rate limit, empty live response, or partial capture.

A fail-closed path should be explicit and reviewable: return an invalid result, raise a narrow error,
write no artifact, or write a clearly non-actionable diagnostic owned by the correct agent. Never bury
it in a permissive fallback.

### 2. Keep Side Effects Behind Owner Rails

The repo is the shared machine contract, but not every path may write every artifact.

- Teammate/offline code may create docs, fixtures, evals, research, RFCs, and propose-only artifacts
  through reviewed PRs.
- Computer-owned paths may use live connectors and may promote, execute, close, kill, or log orders
  only after Charter review gates.
- Tests must not call live connectors. Use dependency injection, static fixtures, and local tempdirs.
- Docs and fixtures must not include secrets, current account balances, live order ids, or instructions
  that could be interpreted as an executable order.
- Any function that can mutate `state/`, `runs/ARMED/`, `runs/EXECUTED/`, `runs/CLOSED/`,
  `runs/KILLED/`, broker state, Slack state, or external services must make that capability obvious in
  its name, type, and call site.

If a change needs live data, specify the request and the sanitized artifact Computer should commit
back for offline review. Do not simulate live authority.

### 3. Use Strong Typed and Schema Boundaries

Every boundary that carries money, state, or provenance needs a contract.

- Prefer dataclasses, typed models, enums, or JSON Schema over loose dicts for artifacts, orders,
  signals, and eval results.
- Parse external data at the edge and convert it into internal types before business logic sees it.
- Validate state transitions, writer/owner roles, timestamps, and prohibited fields before accepting
  repository artifacts.
- Represent money and risk explicitly: currency, quantity, side, instrument, premium vs collateral,
  book basis, cash floor, and phase cap should not be inferred from position in a tuple.
- Treat unknown enum values as invalid unless a forward-compatible schema explicitly quarantines them
  as non-actionable.
- Keep schemas close to fixtures and validators so reviewers can trace a field from example artifact
  to enforcement.

A typed contract should make invalid states unrepresentable where practical and rejected where not.

### 4. Preserve Provenance and Time

No signal should become alpha without lineage.

- Every observed signal needs a source, collection time, and enough raw reference to audit what was
  seen without re-fetching live data.
- Every simulated or derived value must remain labeled as simulated/derived through downstream
  artifacts.
- Proposal provenance should list input artifacts and explain raw-reference limitations.
- Evals must avoid look-ahead by comparing only information available at or before the decision time.
- Confidence should decay or be bounded when evidence is stale, sparse, boilerplate-like, or source
  quality is unknown.

If provenance cannot be preserved, the artifact should be downgraded or rejected rather than promoted.

### 5. Write Slim, High-Value Tests

Tests should buy down actual risk. Prefer a few narrow tests that guard the rail over many generated
cases that assert incidental behavior.

High-value Fund tests usually cover:

- **Safety invariants:** disallowed accounts abort; unknown option structure rejects; `review_*` must
  precede `place_*`; cash floor and sizing caps fail closed.
- **Schema contracts:** valid fixture accepts; execution-authorizing proposed fixture rejects; unknown
  state transition rejects; extra prohibited fields reject.
- **Provenance/time:** missing `observed_at` rejects; simulated cannot masquerade as observed;
  out-of-order or look-ahead series fail evals.
- **Connector seams:** live fetchers are injected; offline tests use fixtures; retries are finite;
  failed captures append nothing actionable.
- **Regression properties:** previous false positives in sentiment normalization remain fixed;
  permutation/placebo checks keep rejecting non-leading signals.

Low-value tests to avoid:

- checking that a mock was called when the safety result is not asserted;
- snapshotting an entire generated Markdown/JSON file when one invariant matters;
- testing private helper names instead of public contract behavior;
- adding broad fixture factories that hide the required fields;
- weakening assertions to match current output after a bug is found.

A good test name should read like a safety claim: `test_proposed_rejects_execution_authorizing_fields`,
`test_missing_observed_at_is_non_actionable`, or `test_unknown_account_aborts_before_review`.

### 6. Prefer Small Designs Over Broad Rewrites

Small, explicit contracts are safer than large AI-authored rewrites.

- Use an RFC when a change revises cross-module contracts, schemas, state machines, connector
  boundaries, eval discipline, or owner responsibilities.
- Keep PRs scoped to one complete behavior. Do not mix rail changes, refactors, fixtures, and strategy
  changes unless the contract requires them together.
- Make rollback simple: a reviewer should be able to remove the PR without corrupting live or generated
  state.
- Avoid abstractions until at least two real call sites need the same contract.
- Do not cleanup unrelated code while touching safety-sensitive paths.

Design should make the next unsafe edit harder, not just make this edit prettier.

### 7. Treat Money-Domain Constraints as Types, Not Comments

Capital safety should not depend on prose reminders alone.

- Account identity and account kind must be checked before any live or execution-adjacent operation.
- Option strategies must be recognized as long call/put, covered call, or cash-secured put before order
  review can pass; all other structures reject.
- Phase caps, cash floors, position sizing, and premium/collateral exposure should be computed from
  validated book state, not hand-entered confidence.
- Kill-switch and circuit-breaker status should be explicit inputs to entry decisions.
- Settlement and buying-power assumptions should be visible at the boundary where they affect action.
- A proposal should never imply that Teammate has observed current buying power, quote, borrow,
  liquidity, halt, PDT, or broker review status.

If a reviewer cannot tell whether a number can move money, ask for stronger typing before approval.

## Review Checklist

Use this checklist for PRs, RFCs, and agent-authored artifacts. A PR does not need to touch every item,
but every touched item should have an answer.

### Authority and Side Effects

- [ ] Does the change stay within the authoring agent's role from `HANDOFF.md`?
- [ ] Does it avoid live connectors, market/account/order APIs, Robinhood, scanners, and deployment
      unless Computer-owned execution explicitly requires them?
- [ ] Does it avoid mutating generated/live state such as `STATE.md`, `runs/QUEUE.json`,
      `runs/SELF_AUDIT.md`, `state/*`, `runs/ARMED/*`, `runs/EXECUTED/*`, `runs/CLOSED/*`, or
      `runs/KILLED/*` from offline paths?
- [ ] Are all side-effecting functions named, injected, and isolated from import-time behavior?

### Fail-Closed Behavior

- [ ] What happens if required data is missing, stale, malformed, or unknown?
- [ ] Does the path abort or produce a non-actionable diagnostic rather than guessing?
- [ ] Are connector failures, empty responses, and partial captures bounded and non-actionable?
- [ ] Are unknown accounts, instruments, states, option structures, and owner/writer combinations
      rejected?

### Typed Contracts and Schemas

- [ ] Is every artifact boundary parsed and validated before business logic consumes it?
- [ ] Are state transitions represented by explicit allowed transitions rather than ad hoc strings?
- [ ] Are money quantities tagged with enough context to prevent unit/account/instrument confusion?
- [ ] Do fixtures demonstrate both a valid case and the highest-risk invalid case?

### Provenance and Time

- [ ] Does every signal preserve source, timestamp, and simulated/observed status?
- [ ] Does the change prevent look-ahead or stale evidence from increasing conviction?
- [ ] Can reviewers trace a proposal's inputs without re-running live capture?
- [ ] Are raw references sanitized and sufficient for offline audit?

### Tests and Evals

- [ ] Are tests narrow, deterministic, offline, and focused on the risky contract?
- [ ] Do tests assert safety outcomes, not just mock calls or snapshots?
- [ ] Are new fixtures minimal and reviewable?
- [ ] Does validation include the narrowest relevant command, such as a specific `pytest` target or
      offline eval?
- [ ] If no test was added, is the reason clear because the change is docs-only or already covered by
      an existing high-value test?

### Design Quality

- [ ] Is the diff small enough to review as one behavior?
- [ ] Are cross-module or owner-boundary changes captured in an RFC?
- [ ] Does the change strengthen or preserve the Charter rails?
- [ ] Is rollback safe and free of live/generated state corruption?

## Reviewer Language

Use direct review language when rejecting AI-code patterns:

- "This defaults missing money/account data into an actionable path. Please fail closed instead."
- "This test mocks away the safety property. Please assert the rail outcome with a minimal fixture."
- "This offline artifact includes execution intent. Keep it `PROPOSED` and remove sizing/order-review
  fields."
- "This changes a state-machine contract without a schema/RFC. Please define the boundary first."
- "This loses provenance or simulated/observed labeling. The signal cannot feed conviction as written."
- "This helper has hidden side effects. Inject the side-effecting dependency and keep imports inert."
- "This broad rewrite makes safety review harder. Please split the contract change from cleanup."

Approval language should be equally concrete:

- "The change preserves Teammate/Computer ownership, validates the artifact boundary, and fails closed
  on unknown state."
- "The tests are slim and cover the high-risk invalid case without live connectors."
- "The proposal keeps provenance and simulation labels intact and does not imply execution authority."

## Minimum Validation Expectations

- Docs-only changes: run a local diff review and, when practical, a Markdown/render sanity check.
- Schema or fixture changes: run the relevant validator/eval against valid and invalid fixtures.
- Python logic changes: run the narrowest targeted `pytest` file or test case first, then broader
  offline evals only if the touched behavior participates in them.
- Safety/execution-adjacent changes: require explicit offline tests for fail-closed behavior and, for
  Computer-owned live paths, separate Computer validation under the Charter rails.

Never run validation that uses live connectors, market data, broker/account/order APIs, scanners,
Slack mutation, deployment, or generated-state mutation from a Teammate/offline PR.

## Examples From Current Repo Contracts

- `docs/integration/fixtures/proposed/invalid-execution-authorizing.json` is the right kind of invalid
  fixture: it proves a proposed artifact cannot smuggle execution authority.
- `evals/proposed_validator.py` is the right kind of boundary: it validates state, writer/owner, and
  prohibited fields before downstream use.
- `tests/test_web_sentiment.py` guards concrete sentiment false positives such as quote boilerplate and
  generic buy-language instead of snapshotting the full normalizer output.
- `tests/test_state_snapshot.py` demonstrates generated-state awareness; changes to live snapshots must
  be intentional and not incidental fallout from unrelated work.
- `HANDOFF.md` is the role boundary reviewers should cite when a Teammate-authored change reaches for
  Robinhood, live finance data, promotion, or execution behavior.
