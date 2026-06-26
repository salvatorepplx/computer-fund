# RFC-002: Integration Substrate Between Teammate and Computer

- Status: Proposed
- Owner: Shared: Teammate owns offline contracts, schemas, PRs, and evals; Computer owns live connectors, broker/account state, review, execution, and observed artifact capture
- Created: 2026-06-26
- Related Beads: `teammate-uyp.12`, follows `teammate-uyp.13`, `teammate-uyp.14`, `teammate-uyp.15`
- Scope Boundary: this RFC is docs/design only. It does not implement live connector calls, Robinhood access, live market data access, account/order APIs, ARMED handoffs, order sizing, order review, or execution behavior. Slack remains a human nudge layer, not the machine contract.

## Problem

The current handoff model overuses Slack-thread prose as if it were the durable machine contract
between Teammate and Computer. Slack is useful for wakeups, summaries, and human visibility, but prose
threads are not typed, replayable, diffable, or CI-validatable. They cannot reliably prove which
schema version, timestamps, provenance fields, eval gates, or boundary constraints were in force when
an artifact moved between agents.

The Fund now has stronger offline contracts from RFC-001 and its follow-up implementation:

- source-weight learning can demote correlated-but-lagging sentiment sources from offline observed
  event histories;
- observed fixture evals withhold lead-lag/CAP credit when required timestamp or provenance fields are
  absent;
- Computer has committed a finance ticker sentiment adapter, a sanitized observed NVDA fixture, and a
  short timestamped NVDA sentiment/price series that illustrates both the promise and the weakness of
  noisy observed data.

Those artifacts point to the same integration need: the repo should become the typed API between
agents. Slack should point humans and Computer's cron at structured artifacts, but the artifacts
should carry the contract.

## Context and Constraints

- `CHARTER.md` is LAW. No look-ahead, no fabrication, every signal is timestamped, simulated data is
  labeled, order review is mandatory before placement, sizing caps remain in force, and kill-switches
  cannot be weakened by integration convenience.
- `HANDOFF.md` currently describes two channels: Slack as the signal bus and the repo as the durable
  substrate. This RFC narrows that split: Slack is the nudge/notification surface; the repo is the
  machine contract.
- Computer owns live connectors, broker access, account state, live quotes, order state, execution,
  and any ARMED/EXECUTED/CLOSED transition that depends on live data. Teammate remains propose-only
  and offline-only.
- PR 13 added offline source weight learning. Its lesson for integration is that artifacts need enough
  source, timestamp, and outcome structure for later attribution, not just summary prose.
- PR 14 added an observed fixture eval. Its lesson for integration is that observed-looking data must
  not receive lead-lag or CAP credit unless `ts`/`observed_at`, `ingested_at`, `event_id`, source,
  venue, simulation label, and raw provenance are present and auditable.
- Latest Computer-side commits add repeated NVDA captures under `runs/sentiment/series/` and raw
  finance ticker sentiment snapshots under `runs/sentiment/raw/`. The sequence is real-shaped but
  still small and noisy: sentiment moves while price is nearly flat. The substrate must preserve that
  uncertainty instead of laundering it into an execution-ready conclusion.
- Computer's runtime is connector-bearing and can be ephemeral; durable state that Teammate should
  inspect must be committed as sanitized repo artifacts.

## Options Considered

1. **Slack prose as the primary contract.**
   - Benefits: already working, low ceremony, good for human-readable collaboration and urgent nudges.
   - Costs: not typed, not schema-versioned, not replayable, easy to omit timestamps/provenance, and
     hard for CI or offline evals to validate.
   - Failure mode: a Slack summary says an artifact is safe or observed while the underlying repo data
     is missing fields that should block lead-lag, CAP, ARMED, or execution trust.

2. **Repo-as-typed-API now.**
   - Benefits: reviewable diffs, strict schemas, immutable-ish history, CI validation, offline replay,
     clear ownership boundaries, and no new long-running service dependency.
   - Costs: git latency, branch/merge conflict handling, and explicit schema migration discipline.
   - Failure mode: agents treat directory movement as enough and bypass schema/eval gates unless CI and
     local validators are mandatory.

3. **Service interface now.**
   - Benefits: lower latency, richer authz, push/pull APIs, and potentially cleaner state-machine
     transactions.
   - Costs: significantly larger operational surface, new credentials/authz, higher blast radius, and
     increased risk of accidentally bridging Teammate into connector/execution authority.
   - Failure mode: service convenience erodes the hard boundary that Computer alone owns live
     connectors and execution.

4. **Hybrid path.**
   - Benefits: use repo-as-typed-API for the authoritative ledger now, then add narrow services later
     only for notifications, schema validation, or read-only indexing.
   - Costs: requires discipline to keep services derivative, not authoritative.
   - Failure mode: a later service becomes the real source of truth without the repo's reviewability.

## Decision

Adopt **repo-as-typed-API now**, with Slack as a human nudge only and service interfaces deferred.
The smallest safe next step is to define strict, versioned JSON artifacts under `runs/` plus offline CI
validators. Computer may read and write connector/execution-bearing artifacts on its side; Teammate may
write propose-only artifacts and validators. Slack messages should link to artifact paths and summarize
state, but no machine should rely on Slack prose for schema fields, timestamps, provenance, safety
status, or execution authority.

Service interfaces may be reconsidered only after the repo contract is stable and only if they preserve
these boundaries:

- repo artifacts remain the authoritative ledger;
- Teammate still has no live connector, broker, account, order, sizing, or execution capability;
- service writes are schema-validated and reviewable through repo artifacts;
- services cannot place, size, confirm, or approve trades.

## Design

### State Machine

Use typed artifacts and explicit directory transitions. Directories are state labels, not permission
bypasses.

```text
runs/PROPOSED/<id>.json   -- Teammate/offline research proposal, never execution-authorizing
runs/ARMED/<id>.json      -- Computer-owned transition after live review inputs and safety checks
runs/EXECUTED/<id>.json   -- Computer-owned record of an actual placed order/fill attempt
runs/CLOSED/<id>.json     -- Computer-owned final or killed outcome record with realized data
runs/KILLED/<id>.json     -- Computer-owned or governance-owned terminal rejection record
```

Immediate implementation should start with schemas and validators before adding or moving any new live
trade artifacts. This RFC does not authorize Teammate to create `runs/ARMED/`, `runs/EXECUTED/`, or
`runs/CLOSED/` records. If existing docs describe Teammate posting an ARMED ticket, this RFC proposes
migrating that into a safer split: Teammate creates `PROPOSED`; Computer may promote to `ARMED` only
after connector-backed review.

### Artifact Classes

The substrate should cover more than trade lifecycle tickets. It should use the same schema discipline
for every cross-agent fact that can affect research trust or execution readiness:

| Class | Example Paths | Writer | Reader | Purpose |
|---|---|---|---|---|
| Research proposal | `runs/PROPOSED/<id>.json` | Teammate | Computer, humans | Offline thesis, dossier links, eval results, requested live checks |
| Live-review packet | `runs/ARMED/<id>.json` | Computer | Teammate, humans | Connector-backed quote/account/safety review and autonomous execution intent |
| Execution record | `runs/EXECUTED/<id>.json` | Computer | Teammate, humans | Actual order/fill/rejection facts, with account/order identifiers redacted as needed |
| Closure record | `runs/CLOSED/<id>.json` or `runs/KILLED/<id>.json` | Computer | Teammate, evals | Realized outcome, kill reason, postmortem fields, CAP rows |
| Observed sentiment | `runs/sentiment/fixtures/*.json`, `runs/sentiment/series/*.jsonl`, future `runs/sentiment/observed/<source>/*.jsonl` | Computer for observed, Teammate for simulated fixtures | Offline validators/evals | Timestamped observed or simulated sentiment events with provenance |
| Raw/sanitized source refs | `runs/sentiment/raw/<source>/...` | Computer | Offline validators/evals | Auditable backing material without exposing connector secrets |
| Eval report | `runs/evals/<id>.json` | Teammate or Computer depending on data source | CI, humans | Reproducible REG/CAP results and source attribution |

### Common Envelope

Every machine-readable cross-agent artifact should use a common envelope before domain-specific
payload fields:

```json
{
  "schema_version": "cf.integration.v1",
  "artifact_id": "2026-06-26-nvda-sentiment-edge",
  "artifact_type": "proposal",
  "state": "PROPOSED",
  "created_at": "2026-06-26T12:00:00Z",
  "updated_at": "2026-06-26T12:00:00Z",
  "writer": "teammate",
  "owner": "computer",
  "source_commit": "<git-sha>",
  "simulated": false,
  "provenance": {
    "inputs": [
      "runs/sentiment/series/TICKER_NVDA.jsonl",
      "runs/sentiment/fixtures/finance_ticker_sentiment_NVDA.json"
    ],
    "raw_refs": [
      "runs/sentiment/raw/finance_ticker_sentiment/NVDA_2026-06-26T1127.txt"
    ]
  },
  "validation": {
    "required_checks": ["schema", "charter", "no_lookahead", "observed_provenance"],
    "passed_checks": []
  },
  "payload": {}
}
```

Envelope rules:

- `schema_version`, `artifact_id`, `artifact_type`, `state`, `created_at`, `writer`, and `payload` are
  mandatory for all artifacts.
- `simulated` is mandatory for data-bearing artifacts and must stay true for synthetic fixtures.
- `source_commit` is mandatory once an artifact is used by a downstream transition.
- `provenance.inputs` and `provenance.raw_refs` must point to repo paths or explicitly explain why no
  raw backing exists.
- `validation.required_checks` must include the checks relevant to the transition; CI must reject an
  artifact that claims passed checks without a matching report.

### Proposal Payload

A Teammate-authored `runs/PROPOSED/<id>.json` should be incapable of placing or implying an order. It
may ask Computer to perform live checks.

```json
{
  "schema_version": "cf.integration.v1",
  "artifact_type": "proposal",
  "state": "PROPOSED",
  "writer": "teammate",
  "payload": {
    "thesis": "NVDA finance sentiment is varying enough to continue measuring, not enough to trade.",
    "entities": ["TICKER:NVDA"],
    "dossier_refs": ["runs/sentiment/series/TICKER_NVDA.jsonl"],
    "offline_eval_refs": ["runs/evals/source_weight_learning-latest.json"],
    "requested_live_checks": ["quote_snapshot", "account_safety_review", "sentiment_capture_refresh"],
    "non_authorizations": ["no_order", "no_sizing", "no_execution_instruction"],
    "open_risks": [
      "Only three observed NVDA points exist; price proxy is nearly flat while sentiment bounces."
    ]
  }
}
```

### ARMED Payload

A Computer-authored `runs/ARMED/<id>.json` is the first state that may contain execution intent. It
must include live review provenance and safety outputs, and it remains Computer-owned. Teammate may
read it for evals but must not create, edit, approve, or promote it.

Required fields should include:

- `reviewed_at`, `review_actor`, and `review_code_version`;
- live quote snapshot reference and timestamp;
- account allowlist and kill-switch status;
- sizing ladder tier, cap check, and rationale, if Computer intends to execute;
- links to the proposal and all eval reports used;
- explicit no-look-ahead timestamp boundary;
- final Computer verdict: `armed`, `killed`, or `needs_more_data`.

### Observed Data Contract

RFC-001 sentiment artifacts are the proving ground for this substrate. Observed records must preserve
the fields that PR 14 now validates:

- stable `event_id`;
- `entity`, `entity_type`, `source`, and `venue`;
- `score` and `confidence` with documented mapping;
- `ts`, `observed_at`, and `ingested_at`;
- `labels.simulated` or equivalent top-level `simulated=false`;
- `raw_ref` and sanitized raw metadata;
- source-specific provenance sufficient to audit why the event exists.

Lead-lag/CAP credit must be withheld when these fields are absent, even if the record is otherwise
plausible. A short observed series such as the current NVDA captures is useful for schema and plumbing
but not enough to prove alpha or authorize a trade.

### Validation and CI

Add validators before relying on the state machine:

1. `schema`: JSON Schema or typed dataclass validation for each artifact type.
2. `charter`: reject artifacts that attempt to weaken Charter rails, skip review-before-place, omit
   account allowlist checks, or blur simulated vs observed data.
3. `ownership`: reject Teammate-authored artifacts outside propose/offline classes; reject Computer
   live artifacts without connector provenance.
4. `timestamp`: reject look-ahead-prone artifacts where decision timestamps are later than data that
   should not have been known.
5. `provenance`: reject observed artifacts missing `event_id`, timestamps, source/venue, raw refs, or
   simulation labels.
6. `transition`: reject invalid moves such as `PROPOSED -> EXECUTED`, `ARMED` without live review, or
   `EXECUTED` without a prior `ARMED`/kill-switch check.
7. `eval-credit`: allow schema presence while withholding lead-lag/CAP credit until sample size,
   timestamps, raw refs, and outcome windows satisfy pre-registered criteria.

CI should run these validators on every PR touching `runs/PROPOSED/`, `runs/ARMED/`,
`runs/EXECUTED/`, `runs/CLOSED/`, `runs/KILLED/`, `runs/sentiment/`, `execution/`, `evals/`, or schema
files. Local commands should stay offline and deterministic; connector-backed validation belongs on
Computer's side and is represented only by committed sanitized artifacts.

### Slack Contract

Slack messages should become pointers, not payloads. Recommended shape:

```text
@computer Proposal ready: runs/PROPOSED/<id>.json
Thesis: one sentence.
Required checks: schema PASS, REG PASS, CAP sample too small / withheld.
Ask: live quote/account/sentiment refresh if you choose; no order authorization from Teammate.
```

Rules:

- Slack never supplies required schema fields.
- Slack never overrides CI, Charter rails, or state-machine ownership.
- Slack may wake Computer, summarize diffs, request connector-owned observation, or notify humans.
- If Slack and repo disagree, the repo artifact plus CI result wins.

## Implementation Sequence

1. **RFC only.** Land this design as the reviewable contract proposal. No schemas, live calls, ARMED
   handoffs, sizing changes, or execution behavior.
2. **Schema scaffold.** Add JSON Schemas for the common envelope, `PROPOSED`, observed sentiment event
   references, and transition records. Include only offline fixtures.
3. **Offline validator.** Add a deterministic validator that checks schema, ownership, timestamp,
   provenance, simulated labels, and transition legality without importing live connector code.
4. **CI wiring.** Run the validator for changed `runs/` artifacts and keep `git diff --check`/offline
   evals as cheap gates.
5. **Migrate proposals.** Introduce `runs/PROPOSED/` for Teammate-authored research proposals and
   update Slack nudges to link to those artifacts.
6. **Computer promotion path.** Let Computer define and own `ARMED`/`EXECUTED`/`CLOSED` writers that
   read validated proposals, fetch live connector/account data, and commit sanitized outputs.
7. **Eval integration.** Feed `CLOSED`/`KILLED` outcome records and observed sentiment series into CAP
   and source-weight learning so downstream weight updates rely on typed artifacts, not prose.
8. **Service reconsideration.** Revisit a narrow service or webhook only after schema/CI/state-machine
   behavior is stable and only as a derivative notification or validation layer.

## Falsifiable Success Criteria

This RFC succeeds only if later implementation can pass these checks:

- A Teammate proposal can be reviewed from `runs/PROPOSED/<id>.json` plus linked artifacts without
  reading Slack prose.
- CI rejects malformed artifacts, missing schema versions, missing timestamps, missing simulation
  labels, missing raw provenance, and invalid state transitions.
- Observed sentiment fixtures that lack timestamp/provenance fields are accepted only as raw/schema
  examples, not as lead-lag or CAP-credit-bearing observations.
- Source weight learning can attribute outcomes by source/venue using repo artifacts alone.
- Computer can promote or kill a proposal using its connector-backed review while keeping live account,
  broker, order, and sizing authority entirely Computer-side.
- Slack messages can be lost, duplicated, or edited without corrupting the durable state machine.
- A closed/killed outcome can be replayed offline into REG/CAP/source-weight reports from repo history.

Failure conditions that should force redesign:

- Any path lets Teammate create or mutate `ARMED`, `EXECUTED`, `CLOSED`, broker/account, sizing, or
  order-intent records.
- A Slack message becomes necessary to reconstruct required machine fields.
- CI cannot distinguish simulated fixtures from observed artifacts.
- Missing timestamp/provenance fields still receive lead-lag/CAP credit.
- Service interfaces become authoritative before the repo schema and transition validators are stable.
- Computer-side live connector artifacts cannot be sanitized enough for repo review while preserving
  auditability.

## Open Questions

- Should `PROPOSED` replace all Teammate-originated ARMED language immediately, or should existing
  `HANDOFF.md` wording be updated only when the schema PR lands?
- What minimum observed sample size should unlock source-specific CAP credit for a new source after
  PR 13's offline learning path? The current NVDA series is intentionally below that threshold.
- Should schema files live under `schemas/`, `runs/schemas/`, or `execution/schemas/`? A neutral
  top-level `schemas/` directory may best reflect the shared contract.
- How much raw connector evidence can Computer safely commit while preserving license, privacy,
  account, and broker constraints?
- Should future service interfaces be limited to read-only artifact indexing, or can Computer-owned
  writers safely expose append-only endpoints that still commit through git?
