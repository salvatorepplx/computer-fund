# AGI Production Standards Inventory for Computer Fund

**Task:** teammate-yr7.3 — import/adapt production standards from `/home/dev/agi`.

**Source provenance:** `/home/dev/agi` was inspected read-only on 2026-06-28T03:26:21Z UTC at commit `3e1aa59c2961bdfd8446759f4f98507bc6cedd9b` on branch `main` with a clean worktree. After `git fetch origin master`, this PR's Computer Fund merge-base is `9d18c1b0173824bd3d88c10e646cbcb5ff3802ff`.

**Boundary:** this inventory adapts engineering practices only. It intentionally does not copy AGI internal service details, run live Computer Fund connectors, call `pplx_sdk`, query market data, touch Robinhood/account/order APIs, run capture/scanner scripts, or mutate observed/generated/live state.

## Executive Summary

The strongest transferable AGI patterns for Computer Fund are:

1. **Agent instructions as enforceable operating law** — central guidance plus local deltas, not scattered tribal knowledge.
2. **High-value tests over test volume** — prefer behavior/integration coverage, assert meaningful failure modes, and avoid mock-heavy slop.
3. **Typed boundaries** — schemas and explicit models at every file/API/state boundary, with unknown fields rejected where safety matters.
4. **Read-only diagnostic loops** — symptom-oriented runbooks, exact evidence capture, owner boundaries, and durable follow-up tables.
5. **Evaluation systems as production assets** — reusable eval libraries, deterministic cohorts, manifests/reports, and resumable runs.
6. **Documentation coupled to interfaces** — changed commands, flags, schemas, APIs, and runtime behavior must update docs/runbooks in the same PR.

For Computer Fund, the adaptation should start as documentation and offline tooling, then progress to CI checks and diagnostic harnesses. Live execution remains with Computer; sal-bot stays offline/propose-only.

## Source-Mapped Patterns

### 1. Agent Instructions as Layered Standards

**AGI evidence**

- `/home/dev/agi/AGENTS.md:7` defines `AGENTS.md` as the canonical coding-agent instruction source.
- `/home/dev/agi/AGENTS.md:14` states root guidance sets repo-wide defaults and local files apply to subtrees.
- `/home/dev/agi/AGENTS.md:15` requires both root and local instructions, with local guidance taking priority when it differs.
- `/home/dev/agi/AGENTS.md:182` says PR descriptions should be reviewer-oriented and include external context only when useful.
- `/home/dev/agi/AGENTS.md:239` says changes to CLI flags, recipes, wrappers, or APIs must update docs, runbooks, help, and call sites.

**Transferable principle**

Computer Fund should make its engineering standards discoverable at the point of work. A root instruction file should encode non-negotiable constraints, while targeted docs can add local details for `execution/`, `state/`, `evals/`, and `research/`.

**AGI-specific details to avoid copying**

Do not copy AGI's Buildkite/Bazel/pnpm/uv monorepo rules, team ownership, or service topology. Computer Fund is a smaller repo and should prefer lightweight scripts and docs until scale justifies heavier machinery.

**Computer Fund adaptation**

- Add a root `AGENTS.md` or equivalent repo-quality standard that explicitly references `CHARTER.md` and `HANDOFF.md` as safety law.
- Add local guidance for safety-critical directories: `execution/` (review-before-place invariants), `state/` (append-only/audit rules), `evals/` (anti-slop test/eval rules), and `research/` (provenance requirements).
- Require PRs that alter commands, schemas, data files, or run loops to update the corresponding docs/runbooks.

### 2. Testing Strategy: Behavior, Integration, and Anti-Slop

**AGI evidence**

- `/home/dev/agi/AGENTS.md:63` tells agents to select the correct unit-test target before running tests.
- `/home/dev/agi/AGENTS.md:65` identifies functional tests as blocking PR checks.
- `/home/dev/agi/AGENTS.md:68` points to detailed coverage checks for changed files.
- `/home/dev/agi/AGENTS.md:136` says to question test value and avoid tests that do not add meaningful coverage.
- `/home/dev/agi/AGENTS.md:137` prefers end-to-end testing over patching/mocking internals for functional tests.
- `/home/dev/agi/AGENTS.md:140` prefers full mock-call assertions instead of weakened partial assertions.
- `/home/dev/agi/AGENTS.md:141` rejects tests that assert nothing meaningful, over-mock the behavior under test, or chase quantity over coverage.
- `/home/dev/agi/docs/dev-guide/08-testing.md:3` frames testing as confidence in code changes before release.
- `/home/dev/agi/docs/dev-guide/08-testing.md:28` separates unit, integration, and functional tests by responsibility.

**Transferable principle**

Tests should fail when real safety or alpha-relevant behavior regresses. For a money-adjacent autonomous trading repo, the highest-value tests are offline behavioral tests around review gates, sizing, account allowlists, schema parsing, state transitions, and diagnostic summaries.

**AGI-specific details to avoid copying**

Do not import AGI's Bazel targets, backend functional-test harness, Docker Compose services, or coverage infrastructure directly. Computer Fund can enforce the same principles with a small Python test suite and explicit fixtures.

**Computer Fund adaptation**

- Define test tiers in `evals/README.md` or a new testing standard:
  - **Unit:** pure score/risk/state helpers with deterministic fixtures.
  - **Contract:** JSON/JSONL/state/schema parsing for `state/`, `runs/`, and `execution/` artifacts.
  - **Offline functional:** full propose/review simulation with stubbed broker responses and no live connectors.
  - **Diagnostic regression:** replay incident fixtures and verify summary/follow-up output.
- Ban low-value tests that mock the exact behavior under test, assert only implementation calls, or merely snapshot prompt text.
- Require any execution-safety PR to include at least one test that would fail if a rail were bypassed.

### 3. Typed Boundaries and Schema Discipline

**AGI evidence**

- `/home/dev/agi/AGENTS.md:145` calls frequent runtime type checks a code smell and recommends better type design.
- `/home/dev/agi/AGENTS.md:153` requires explicit structures such as dataclasses, `NamedTuple`, `TypedDict`, and Pydantic models instead of `dict[str, Any]` across module boundaries.
- `/home/dev/agi/protobuf/AGENTS.md:37` states proto codegen owns checked-in Python generation and avoids hand-written generated wrappers.
- `/home/dev/agi/protobuf/AGENTS.md:47` describes choosing generated message, service, or Pydantic bindings based on consumer needs.
- `/home/dev/agi/protobuf/AGENTS.md:65` says generated update targets prune stale files so renamed/removed proto files are reflected in source.
- `/home/dev/agi/pplx/evals/public_evals/pplx_evals/benchmarks.py:16` defines typed benchmark source specs with Pydantic.
- `/home/dev/agi/pplx/evals/public_evals/pplx_evals/benchmarks.py:17` uses `ConfigDict(extra="forbid")` for strict unknown-field rejection.
- `/home/dev/agi/pplx/evals/public_evals/pplx_evals/benchmarks.py:29` constrains numeric fields with `Field(..., ge=1)`.

**Transferable principle**

Every boundary that crosses from untrusted or persisted data into decision logic should parse into a typed, validated model. Unknown fields should be rejected in safety-critical schemas so stale or hallucinated fields cannot silently alter behavior.

**AGI-specific details to avoid copying**

Computer Fund does not need protobuf/codegen unless it grows a multi-language API. The transferable part is schema ownership, generated/stale-file discipline, and strict parsing — not AGI's proto tree.

**Computer Fund adaptation**

- Define explicit Pydantic/dataclass models for:
  - risk phase state (`state/risk_phase.json`),
  - order log entries (`state/order_log.jsonl`),
  - proposed trade/review objects,
  - research observation records,
  - eval manifests/reports.
- Use `extra="forbid"` and constrained fields for all safety-critical persisted data.
- Keep raw observed data separate from normalized typed records; never let raw connector dictionaries flow directly into execution decisions.
- Add offline schema validation commands that inspect fixtures and historical repo state without calling live connectors.

### 4. Read-Only Diagnostics and Incident Runtime Loops

**AGI evidence**

- `/home/dev/agi/docs/agent_api/lights-out/README.md:3` defines a first-pass RCA operational knowledge base.
- `/home/dev/agi/docs/agent_api/lights-out/README.md:5` explicitly says the KB is not an append-only update log, PR diary, raw evidence archive, or monitor-prompt dump.
- `/home/dev/agi/docs/agent_api/lights-out/README.md:9` routes readers to scope, service map, monitors, recipes, alert triage, safe read-only tools, and incidents.
- `/home/dev/agi/docs/agent_api/lights-out/README.md:34` says symptom-to-recipe mappings should be promoted after repeated incidents or confidence-building investigations.
- `/home/dev/agi/docs/agent_api/lights-out/README.md:44` says active incidents use an incident folder as live state and recovery should promote durable lessons to stable KB pages.
- `/home/dev/agi/docs/agent_api/lights-out/incidents/2026-06-13-responses-5xx-sapi-llm/README.md:31` separates contributors to an incident instead of collapsing causality.
- `/home/dev/agi/docs/agent_api/lights-out/incidents/2026-06-13-responses-5xx-sapi-llm/README.md:67` records that Teammate did not mutate production, Datadog, Terraform, Kubernetes, Slack config, shared config, or provider routing.
- `/home/dev/agi/docs/agent_api/lights-out/incidents/2026-06-13-responses-5xx-sapi-llm/README.md:72` captures durable lessons.
- `/home/dev/agi/docs/agent_api/lights-out/incidents/2026-06-13-responses-5xx-sapi-llm/README.md:91` tracks follow-up actions with type, owner/bead, and state.
- `/home/dev/agi/docs/dev-guide/15-observability.md:5` requires timestamp anchoring with real epoch commands instead of assumptions.
- `/home/dev/agi/docs/dev-guide/15-observability.md:16` requires dashboard JSON/schema validation and verifying metric names/tags/units before sharing.
- `/home/dev/agi/docs/dev-guide/15-observability.md:47` warns against high-cardinality metrics that can time out or silently drop data.

**Transferable principle**

Diagnostics should be safe, repeatable, and source-mapped. They should distinguish observation from mutation, route symptoms to recipes, and preserve durable lessons without turning incident docs into noisy raw logs.

**AGI-specific details to avoid copying**

Do not copy AGI Datadog, Kubernetes, Terraform, provider-routing, or SAPI/Echolot details. Computer Fund's diagnostics are local/offline and should operate on repo artifacts, fixtures, and Computer-authored disclosures.

**Computer Fund adaptation**

- Create `runs/incidents/README.md` with:
  - scope and exclusions,
  - symptom-oriented local recipes,
  - an incident folder template,
  - follow-up table format,
  - explicit sal-bot no-mutation boundary.
- Add read-only recipes such as:
  - `rail_breach_review.md` — inspect order-log/review artifacts for rail violations,
  - `missing_provenance.md` — trace research signal timestamps and raw evidence,
  - `state_drift.md` — compare declared `STATE.md` against typed `state/*.json`,
  - `eval_regression.md` — replay offline fixtures and summarize failures.
- Require diagnostics to record exact artifact paths, access timestamp, commit hash, and whether evidence is observed/raw/simulated.

### 5. Eval Systems as Reusable Production Infrastructure

**AGI evidence**

- `/home/dev/agi/pplx/evals/AGENTS.md:9` says eval scripts/notebooks should build generic, shareable libraries rather than one-off inline code.
- `/home/dev/agi/pplx/evals/AGENTS.md:27` says common functionality should be extracted into reusable classes or functions.
- `/home/dev/agi/pplx/evals/AGENTS.md:67` through `/home/dev/agi/pplx/evals/AGENTS.md:71` names stable modules for datasets, rollouts, graders, reports, and prompts.
- `/home/dev/agi/pplx/evals/AGENTS.md:105` says README files must be updated when modifying APIs or adding features.
- `/home/dev/agi/pplx/evals/AGENTS.md:125` through `/home/dev/agi/pplx/evals/AGENTS.md:131` says docs should include API references, examples, workflows, integration examples, and best practices.
- `/home/dev/agi/docs/memory/wiki_eval_system.md:160` describes deterministic per-user sampling so time series remain coherent.
- `/home/dev/agi/docs/memory/wiki_eval_system.md:196` distinguishes two eval loops that answer different questions and read different prefixes.
- `/home/dev/agi/docs/memory/wiki_eval_system.md:223` describes a bounded refire pass for transient failed cells and avoids repeated refires.
- `/home/dev/agi/docs/memory/wiki_eval_system.md:233` says daily eval outputs include `manifest.json`, `report.json`, and `report.md`.

**Transferable principle**

Evaluation should be a repeatable system with stable inputs, typed manifests, reports, and bounded retry semantics. It should answer one clear question per lane and make results comparable over time.

**AGI-specific details to avoid copying**

Do not copy AGI's wiki/memory eval domains, S3 buckets, ConfigBoard, Eppo gates, Datadog metrics, or cron infrastructure. Computer Fund should keep offline JSON/Markdown reports in-repo until there is a safe need for external storage.

**Computer Fund adaptation**

- Split Computer Fund evals into lanes:
  - **Safety rail evals:** account allowlist, review-before-place, sizing, kill switch, permitted option structures.
  - **Signal hygiene evals:** timestamp integrity, no look-ahead, raw-vs-simulated labels, provenance completeness.
  - **Alpha thesis evals:** falsification harnesses, null/permutation comparisons, post-trade calibration.
  - **Agent-loop evals:** whether Teammate comments identify weak typing, goal-fitting tests, and missing diagnostics.
- Standardize eval output as `manifest.json`, `report.json`, and `report.md` under `runs/evals/<date-or-run-id>/`.
- Make cohorts deterministic for longitudinal comparisons: fixed fixture IDs, stable ticker sets for offline tests, and explicit sample manifests.
- Implement one bounded retry/refire policy for transient offline failures; do not let retries mask deterministic failures.

### 6. Code-Health Practices for Agent-Generated Code

**AGI evidence**

- `/home/dev/agi/AGENTS.md:132` says comments should explain why, not obvious what.
- `/home/dev/agi/AGENTS.md:135` says to combine redundant tests.
- `/home/dev/agi/AGENTS.md:145` treats repeated runtime type probes as poor type design.
- `/home/dev/agi/AGENTS.md:149` says shell-command inputs should be treated as untrusted and validated with strict allowlists.
- `/home/dev/agi/AGENTS.md:151` recommends guard clauses and early exits over nested control flow.
- `/home/dev/agi/AGENTS.md:155` prefers pure functions that depend on inputs and return new values instead of mutation.

**Transferable principle**

Computer Fund should optimize for small, auditable, deterministic code. This matters more than general application polish because a weak abstraction or hidden mutation can become a financial safety bug.

**AGI-specific details to avoid copying**

Do not copy AGI language-specific conventions wholesale. Keep Computer Fund's current Python-first style, but add safety-focused restrictions where they reduce risk.

**Computer Fund adaptation**

- Prefer pure transformation functions for scoring, risk checks, state diffs, and report generation.
- Validate shell/file identifiers with allowlists before running local scripts.
- Keep connector/live-data code behind explicit boundaries owned by Computer, not sal-bot.
- Reject PRs that add broad `dict` plumbing, hidden state mutation, or test fixtures that silently encode the expected answer.

## Recommended Staged Adoption Plan

### Stage 0 — Adopt the Standards in Documentation

**Goal:** create the operating contract before adding automation.

- Add root agent/review guidance that imports the `CHARTER.md` rails and `HANDOFF.md` proposes/disposes boundary.
- Add a testing standard that bans slop tests and defines offline unit/contract/functional/diagnostic tiers.
- Add typed-boundary standards for state, review, order-log, research, and eval artifacts.
- Add an incident/runbook skeleton under `runs/incidents/`.

**Exit criteria**

- A reviewer can tell which rules apply before touching `execution/`, `state/`, `research/`, or `evals/`.
- Every new safety-sensitive artifact has an identified schema owner, even if not yet enforced in CI.

### Stage 1 — Add Offline Validation Contracts

**Goal:** convert the most important standards into local checks without live connectors.

- Add Pydantic/dataclass models for persisted state and review artifacts.
- Add schema validation fixtures and commands that read only repository files.
- Add regression tests for account allowlist, sizing ladder, review-before-place, kill switch, and option-structure restrictions.
- Add eval output conventions: `manifest.json`, `report.json`, `report.md`.

**Exit criteria**

- `pytest` or an equivalent local command can prove core rails against fixtures.
- Invalid persisted state fails closed instead of being tolerated as unknown fields.

### Stage 2 — Build Read-Only Diagnostic Loops

**Goal:** make failures teach the repo without granting sal-bot live powers.

- Add symptom-to-recipe runbooks for rail breach, provenance gap, state drift, eval regression, and post-trade disclosure mismatch.
- Add a local diagnostic script that reads committed artifacts and emits a Markdown incident summary.
- Add incident templates with summary, evidence, contributors, durable lessons, and follow-up table.
- Require exact commit/access timestamps and raw/simulated/observed labels in incident evidence.

**Exit criteria**

- A teammate can investigate a failure from repo artifacts only and produce a source-mapped follow-up plan.
- Durable lessons are promoted back into stable docs instead of buried in raw logs.

### Stage 3 — Operationalize Agent Review

**Goal:** make the standards part of every future Teammate/Computer engineering loop.

- Add reviewer checklists for weak typing, goal-fitting tests, missing runbooks, and unsafe live boundaries.
- Add CI or pre-PR checks for schema validation, offline tests, and documentation drift.
- Add eval lanes for safety rails, signal hygiene, alpha thesis falsification, and agent-loop quality.
- Track follow-ups as Beads or repo TODOs with owner/state, not loose prose.

**Exit criteria**

- PRs changing execution or state cannot pass without meaningful offline validation.
- Agent-generated code is reviewed for production risk patterns, not only syntax.

## Suggested Near-Term PRs

1. **Root standards PR:** add `AGENTS.md` with Computer Fund-specific safety, testing, typing, and no-live-connector guidance.
2. **Testing standards PR:** document test tiers in `evals/README.md` and add one or two high-value safety fixtures.
3. **Typed state PR:** introduce models for `risk_phase`, proposed order reviews, and order-log entries with strict parsing.
4. **Incidents/runbooks PR:** add `runs/incidents/README.md` and templates/recipes for read-only diagnostics.
5. **Eval artifact PR:** define `manifest.json`, `report.json`, and `report.md` conventions for offline eval runs.

## Risks and Guardrails

- **Risk: overfitting to AGI scale.** Keep Computer Fund standards lightweight until a real repeated failure justifies automation.
- **Risk: docs without enforcement.** Stage 1 should quickly add offline schema/tests for the highest-risk rails.
- **Risk: sal-bot boundary creep.** Every diagnostic recipe must state read-only inputs and explicitly forbid live connectors, Robinhood APIs, market-data fetches, capture scripts, and state mutation.
- **Risk: test theater.** Reviewers should reject tests that merely freeze generated text or mock the behavior being tested.
- **Risk: hidden schema drift.** Unknown persisted fields should fail validation in safety-critical paths.
