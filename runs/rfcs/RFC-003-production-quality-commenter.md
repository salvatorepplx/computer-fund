# RFC-003 — Production-Quality Commenter Agent

## Status

Draft proposal for Bead `teammate-yr7.2`. This RFC designs a reviewer/commenter agent for the
Computer Fund. It is propose-only: no live connectors, no broker/account/order/scanner APIs, no
capture runs, no state promotion, and no comments on human or other-agent PRs unless explicitly
assigned.

## Problem

The Fund is money-adjacent and increasingly agent-written. The core risk is not only ordinary bugs;
it is AI-generated goal-reaching code that appears to satisfy the immediate prompt while degrading the
system's safety, evidence, and maintainability. Common failure modes include:

- Tests that prove the submitted implementation rather than protecting behavior.
- Fail-open behavior around stale state, missing live data, ambiguous schemas, or owner boundaries.
- Weak typed contracts between Teammate's offline proposals and Computer-owned execution paths.
- Hidden live/action side effects in scripts that look like analysis or capture helpers.
- Research write-ups that overstate simulated or under-sampled evidence as production edge.
- Missing design principles, provenance, and falsifiers, making future agents repeat old mistakes.

The commenter should make these risks visible continuously, while remaining structurally incapable of
trading, live data access, state mutation, or PR interference.

## Non-Goals

- It does not place, size, review, route, confirm, or promote trades.
- It does not call Robinhood, live market/account/order APIs, scanner APIs, Slack write APIs, or
  capture scripts.
- It does not auto-merge, enqueue, deploy, or mark PRs ready.
- It does not block Computer-owned live decisions directly; it produces repo/PR/Bead evidence for
  humans or Computer-owned loops to consume.
- It does not comment on PRs created by humans or other agents without explicit assignment.

## Inputs It May Read

- `CHARTER.md`, `CONSTITUTION.md`, `HANDOFF.md`, `TEAMMATE_GOAL.md`, `STATE.md`.
- `corpus/improvement_log.md`, `corpus/lessons.md`, `runs/CORPSES.md`, `runs/QUEUE.json`.
- Offline code, schemas, docs, and tests in `evals/`, `schemas/`, `tests/`, `research/`, `sim/`,
  `graph/`, and propose-only `runs/` paths.
- PR diffs, CI logs, Bead metadata, and attached design artifacts.
- Static file metadata such as touched paths, import graph, and test commands declared in docs.

It may inspect `execution/` for safety-review purposes, but it should treat execution semantics as
Computer-owned and propose changes only through explicit review artifacts or dedicated beads.

## Rubric

Each review emits findings with severity, owner boundary, evidence, and a concrete remediation. The
commenter should prefer fewer high-confidence comments over broad style noise.

Severity levels:

- **Blocker** — could violate Charter rails, authorize/enable execution from the wrong owner, fail open
  in money-affecting paths, mutate live/action state, or materially misrepresent production edge.
- **Major** — weakens typed contracts, validation, falsification, provenance, observability, or tests in
  ways that can mask future money-domain failures.
- **Minor** — maintainability, documentation, or ergonomics issue that increases future agent slop but
  does not currently endanger safety rails.
- **Note** — non-blocking observation, positive pattern, or follow-up bead suggestion.

### 1. Safety and Owner Boundaries

Block if any change:

- Lets Teammate create, edit, or imply `runs/ARMED/`, `runs/EXECUTED/`, `runs/CLOSED/`, or
  `runs/KILLED/` state transitions.
- Adds order, sizing, account, buying-power, route, review, confirmation, or execution intent to
  Teammate-authored `PROPOSED` artifacts.
- Touches live Robinhood/account/order/scanner/market APIs from propose-only code paths.
- Changes `CHARTER.md` rails without explicit PR review and human ownership.
- Introduces ambiguous account selection, non-allowlisted account handling, or fallback account behavior.

Major if a change:

- Mixes Computer-owned execution code with offline research/eval code without a typed boundary.
- Uses Slack prose, logs, or free-form docs as a machine contract instead of validated repo artifacts.
- Reads `STATE.md` without checking that its recorded HEAD may lag current git HEAD.

### 2. Fail-Closed Behavior

Block if missing, stale, malformed, or ambiguous inputs default to proceed in:

- Safety rail checks, schema validators, state transitions, alpha-pipeline handoff, or any path that can
  influence a future live review.
- Live-check requests, connector-backed fields, market timestamps, or account-derived fields.

Major if code handles failures with silent defaults, broad `except Exception` fallbacks, empty captures,
or placeholder values without emitting a reviewable reason and preserving a conservative state.

Preferred pattern: reject by default, include a diagnostic reason, and require an explicit owner to
refresh or override through a typed artifact.

### 3. Typed Contracts and Schemas

Major or blocker depending on proximity to execution if:

- New cross-agent artifacts lack schemas, fixture examples, and offline validators.
- Existing schema fields are loosened to `additionalProperties: true` without a documented reason.
- Validation duplicates diverging rules instead of sharing constants or fixtures where practical.
- Unstructured Markdown is used where another agent is expected to parse required fields.

Preferred pattern: small JSON schema or dataclass boundary, checked-in positive and negative fixtures,
and an offline validator included in `python -m evals.run_offline_evals` when relevant.

### 4. Evidence, Provenance, and Anti-Overclaiming

Block if a PR or Bead presents simulated, stale, under-sampled, or connector-inaccessible data as live,
observed, production-grade edge.

Major if research/eval artifacts omit:

- Source paths, timestamps, sample counts, and known limitations.
- Falsifiers that would kill the thesis.
- Distinction between simulated, observed, captured, projected, and Computer-refreshed data.
- Universe membership and cross-sectional coverage when claiming generalization.

Preferred pattern: explicit `simulated:true/false`, provenance refs, raw/input refs or explanation,
minimum sample thresholds, and visible open risks.

### 5. Test Quality and Eval Discipline

Major if tests:

- Mostly assert mocks, implementation wiring, snapshots, or prompt text rather than external behavior.
- Only cover happy paths for validators, safety rails, parsers, or handoff formats.
- Encode the current bug or desired answer without a negative/control fixture.
- Require live connectors, network, broker/account state, or mutable generated state.

Preferred pattern: narrow deterministic tests with at least one meaningful negative/control case, plus
an offline eval hook when the behavior is a system invariant rather than a unit-level contract.

Block if a PR changes safety, handoff, schema, or eval behavior without any command that can be run
offline to exercise the changed invariant.

### 6. Production Maintainability

Major if a change:

- Adds a large multi-purpose script instead of a small composable module and CLI wrapper.
- Hides stateful behavior in import-time side effects.
- Hardcodes timestamps, tickers, paths, or thresholds without an explicit reason and test fixture.
- Duplicates business logic across validator, docs, and runtime code without a synchronization plan.
- Makes future agent edits likely to skip important invariants because docs and code disagree.

Minor if naming, layout, or docs make owner boundaries or validation commands hard to discover.

### 7. Documentation and Design Principles

Major if a new subsystem lacks a short design note covering:

- Owner boundary: Teammate, Computer, human, or repo contract.
- Inputs/outputs and whether data is live, observed, simulated, or generated.
- Fail-closed cases and forbidden actions.
- Required offline validation commands.
- How failures flow into `corpus/lessons.md`, `runs/CORPSES.md`, Beads, or follow-up PRs.

## Comment Format

Use a compact, reviewable format:

```text
[Production-quality: Major] Fail-closed missing for stale STATE.md

Evidence: STATE.md records HEAD <hash>, but this script reads it as current truth without comparing to git HEAD.
Risk: an agent can act on stale signal status and overstate edge readiness.
Remediation: compare STATE header HEAD to current HEAD/origin before using it, or emit an explicit stale-state diagnostic and abort.
Owner boundary: Teammate offline reviewer; Computer must refresh connector-backed state.
```

Rules:

- Cite exact file paths and line numbers when commenting on diffs.
- State why the issue matters in the money-domain, not just style.
- Prefer one comment per root cause; group duplicates.
- Include a positive note when a PR materially strengthens safety/evals.
- For auto-generated reports, include a summary table and only the top findings inline.

## Integration Points

### 1. Repo Patrol

Purpose: periodically scan `origin/master` for production-quality drift and open or update Beads, not
PR comments.

Safe inputs:

- Current repo tree and git history.
- `corpus/improvement_log.md`, `runs/QUEUE.json`, `STATE.md`, `evals/README.md`, `runs/CORPSES.md`.
- Static analysis of imports, file ownership, schema/test coverage, and docs references.

Outputs:

- A Markdown patrol report under `runs/audits/` or a Bead comment owned by the patrol.
- Follow-up Bead suggestions with evidence and priority.
- No edits to generated live state, capture outputs, Computer-owned transition folders, or execution
  behavior unless separately scoped through PR.

Initial patrol checks:

- `STATE.md` header HEAD differs from current `origin/master` HEAD: report stale front-door risk.
- No `.github/workflows/` CI is present: report missing required offline validation gate.
- Any schema or validator change not represented in `evals/run_offline_evals.py`.
- Any `runs/PROPOSED/` artifact that fails `evals.proposed_validator`.
- Any tests or evals importing live connector modules or writing outside temp dirs.
- Any queue/improvement item with `execution` or `Computer` ownership that lacks explicit coordination.

### 2. PR Review

Purpose: comment on assigned PRs before human review, with no autonomous merges.

Trigger modes:

- Explicit assignment by master/human to a specific PR.
- Teammate-created PRs owned by this commenter agent.
- Optional future label such as `production-quality-review`, if humans approve.

Preflight:

- Confirm base is current `origin/master` or disclose divergence.
- Classify touched paths by owner: Charter/law, execution, schema/handoff, eval/test, research/docs,
  generated state.
- Run only static inspection and safe offline commands.

Review gates:

- Blocker comments for Charter/owner-boundary/fail-open issues.
- Major comments for weak tests, weak schemas, missing provenance, or undocumented design decisions.
- Summary includes suggested offline validation commands and any tests not run.

### 3. Bead Gating

Purpose: make Beads harder to close with slop.

Suggested close checklist for production-impacting Beads:

- Scope states owner boundary and forbidden live/action side effects.
- Acceptance criteria include an offline validation command or explicit docs-only reason.
- Implementation evidence distinguishes observed, simulated, generated, and live-refreshed data.
- Any safety/handoff/schema change has at least one negative fixture or fail-closed test.
- Remaining risks are captured as follow-up Beads, not hidden in PR prose.
- If the Bead touches Computer-owned execution semantics, it records explicit coordination status.

The commenter can produce a `PASS / WARN / BLOCKED` gate note. It should not change Bead status unless
that is the assigned task.

### 4. Docs Checklist

Add this checklist to design docs and meaningful PR bodies:

- [ ] Owner boundary is explicit.
- [ ] Forbidden actions are explicit.
- [ ] Inputs/outputs are typed or intentionally prose-only.
- [ ] Missing/stale/ambiguous input behavior fails closed.
- [ ] Simulated vs observed vs live-refreshed data is labeled.
- [ ] Provenance includes repo paths, timestamps, sample counts, or a reason raw refs are unavailable.
- [ ] Offline validation commands are listed and connector-free.
- [ ] Tests include meaningful negative/control coverage when behavior can affect money-domain safety.
- [ ] Follow-up risks are linked to Beads or `corpus/improvement_log.md`.

### 5. Offline Eval Hooks

The commenter should initially recommend, not implement, these hooks:

- `evals.production_quality_static`: connector-free static checks for forbidden action-state paths,
  schema/eval synchronization, generated-state edits, and live connector imports in offline code.
- `evals.pr_rubric_fixture`: small positive/negative synthetic diffs or manifests that exercise the
  rubric without depending on GitHub APIs.
- `evals.docs_checklist`: validates that new RFCs or production-impacting docs include owner boundary,
  fail-closed behavior, validation commands, and provenance sections.
- `evals.bead_gate_fixture`: validates a Bead close-note template against required evidence fields.

These should be wired into `python -m evals.run_offline_evals` once stable, preserving the current
stdlib-only and connector-free property.

## High-Priority Existing Gaps

These are suitable follow-up Beads/PRs found from current `origin/master` inspection.

1. **Add CI for offline validation.** There is no `.github/workflows/` directory, so the repo has no
   GitHub-side gate for `python -m evals.run_offline_evals`, focused pytest tests, proposed-artifact
   validation, or whitespace checks. This is the highest-leverage anti-slop gate.
2. **Add a production-quality static eval.** The current offline harness is strong for specific Fund
   invariants, but it does not yet patrol forbidden path edits, live connector imports from offline
   modules, generated-state edits, schema/eval drift, or docs checklist coverage.
3. **Make stale `STATE.md` detection operational.** `STATE.md` correctly warns that its header HEAD can
   lag git HEAD, but agents still need a deterministic check or helper that reports stale front-door
   state before using it as current truth.
4. **Close settlement-aware buying-power design.** `EXEC-SETTLE-1` remains open/blocked because cash
   account T+1 settlement is execution-safety-adjacent. The commenter should keep this visible as a
   fail-closed design gap requiring Computer/owner coordination.
5. **Fix current PROPOSED timestamp validation drift.** On current `origin/master`,
   `python -m evals.run_offline_evals` fails `eval_proposed_artifact_validator` because
   `runs/PROPOSED/battle-RDDT-leadlag-2026-06-28.json` uses a fractional-second `created_at` timestamp
   that the offline validator rejects. This is exactly the kind of schema/runtime drift the commenter
   should surface before more generated proposals accumulate.
6. **Broaden negative fixtures for handoff and schema edges.** `evals.proposed_validator` already has
   positive/negative fixtures for execution authorization and invalid state, but future work should add
   regression fixtures for stale provenance, missing validation evidence, over-broad requested live
   checks, and schema/docs drift.
7. **Document PR review and Bead close templates.** Current docs describe repo-as-contract and evals,
   but not a standard production-quality PR/Bead checklist. This RFC can seed that follow-up.
8. **Keep simulated/research evidence from becoming trigger language.** Existing docs mostly label this
   well; the commenter should patrol new research artifacts and `runs/PROPOSED/` files for overclaiming
   when sample counts, permutation gates, or cross-sectional coverage are insufficient.

## Rollout Plan

1. **Manual reviewer mode:** use this RFC as a checklist for assigned PRs and Beads only.
2. **Repo patrol report:** add a connector-free static report command that writes Markdown findings but
   does not comment or mutate task state.
3. **CI advisory mode:** run static production-quality evals in CI as non-blocking warnings.
4. **CI required mode:** after false positives are low, require offline evals and static checks for PRs.
5. **Bead gate integration:** require a production-quality close note for safety/schema/handoff/eval
   Beads before marking complete.

## Open Questions

- Should `execution/` changes by Teammate be entirely prohibited, or allowed as offline PR proposals
  when explicitly scoped and coordinated with Computer?
- Should generated files like `STATE.md` and sentiment series be blocked in ordinary PRs unless the PR
  is a capture/state-refresh PR?
- What label or Bead field should trigger PR review once the commenter moves beyond manual assignment?
- Should the first implementation be a Python static checker, a Teammate skill/agent prompt, or both?
