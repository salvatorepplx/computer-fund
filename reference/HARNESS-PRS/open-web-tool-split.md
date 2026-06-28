# HPR: Open-Web Tool Split

- Status: Proposed
- Owner: Shared
- Related Beads: `teammate-00e`
- Created: 2026-06-28

## Problem

`reference/CAPABILITY_INVENTORY.md` shows that the Fund environment includes broad CLI, SDK,
sandbox, GitHub, Python, and open-web surfaces. The autoresearch loop should exploit the ability to
learn widely, but the Fund also has hard safety rails: authority to act, own observed signal series,
promote state, size positions, or touch execution remains Computer-only.

The ambiguous part is not whether tools exist. It is which agent may use which class of tool, and for
what artifact. Over-constraining `sal-bot` makes ordinary literature, OSS, vendor-doc, and public
dataset research unnecessarily dependent on Computer. Over-permitting `sal-bot` risks treating open
web, SDK, market, or execution capability as permission to write observed signals or influence live
state.

This proposal separates capability to **learn** from authority to **act**.

## Context and Constraints

- `CHARTER.md` is LAW. Account allowlist, review-before-place, sizing ladder, kill switches,
  no-look-ahead/no-fabrication, and post-trade transparency are unchanged.
- Computer owns live market/account/execution authority, Robinhood/account/order APIs, sizing,
  kill-switch interpretation, scanners, signal capture, observed signal series, and
  `PROPOSED -> ARMED -> EXECUTED` promotion.
- `sal-bot`/Teammate may propose, structure, test, and document. It must not create or mutate
  Computer-owned live state or observed signal series.
- Open web for literature, OSS, vendor documentation, and public-dataset research is not itself
  "live capture" when it touches no market feed, account data, scanner, signal capture path, observed
  state, or execution path, and when it does not write observed signal series.
- The `pplx_sdk` credential preset remains Computer-owned for signal capture. Possible future
  `academic` or `secgov` use by `sal-bot` for dossier evidence is later/gated and is not authorized by
  this proposal.

## Bounded Capability Probe Results

Computer requested bounded empirical checks for this worker shell. These checks were limited to a
single reachability probe plus local tool availability; no papers were downloaded, no repositories were
cloned, and no packages were installed.

- `curl -sS -m8 -o /dev/null -w "%{http_code}" https://arxiv.org` returned `200`.
- `command -v gh && gh auth status` found `/home/dev/agi/bin/gh`; GitHub auth was active for
  `github.com` over HTTPS with token scopes reported as `read:org`, `read:user`, `repo`, `user:email`,
  and `workflow`.
- `command -v pip || command -v pip3 || python -m pip --version` found `/usr/local/bin/pip`.

## Decision

Adopt a split where capability to **learn** is wide for both Computer and `sal-bot`, but authority to
**act** and to own observed signal state is Computer-only.

`sal-bot` is allowed to use public web, OSS repositories, vendor docs, public datasets, repo/GitHub,
Beads, Slack, Notion when configured, and approved internal read-only systems for literature and
mechanism research. Outputs must be research artifacts: dossiers, RFC/HPR notes, implementation plans,
offline evals, docs, or code that consumes committed/sanitized artifacts.

Computer remains the only actor for live market/account/execution/Robinhood/finance/sentiment-signal
capture, observed-series mutation, ARMED/execution state, sizing, kill switches, and promotion. A
`sal-bot` research artifact may request Computer capture or review, but it cannot become observed
signal input or execution intent by itself.

## Ownership Matrix

| Capability class | `sal-bot` / Teammate | Computer | Artifact boundary |
|---|---|---|---|
| Repo, GitHub, Beads, Slack | Allowed within role and repo policy | Allowed | PRs, Beads, Slack pointers, docs |
| Notion and approved internal read-only systems | Allowed when configured and scoped | Allowed | Research notes, links, summaries, sanitized evidence |
| Public web for literature/mechanism research | Allowed with provenance; no signal-series writes | Allowed | Dossiers, RFC/HPR docs, citations, snapshots when license permits |
| OSS repositories and vendor docs | Allowed for study; no arbitrary cloning/installing unless task-scoped | Allowed | Code references, design notes, dependency/eval proposals |
| Public datasets | Allowed for literature/dossier evidence only when licensing and provenance are clear | Allowed | Research evidence, not observed signal series unless Computer captures/promotes |
| `pplx_sdk.search.web` and other SDK signal-capture presets | Not authorized | Computer-owned | Computer commits sanitized capture outputs if useful |
| Future `academic` / `secgov` SDK preset | Not authorized now; possible gated dossier-evidence lane later | Allowed if Computer chooses | Future accepted rail must define provenance and deny signal capture |
| Finance, live market feeds, sentiment-signal capture, scanners | Forbidden | Computer-only | Computer-owned observed artifacts |
| Robinhood, account, order, broker, execution APIs | Forbidden | Computer-only under Charter rails | Computer-owned review/execution/state artifacts |
| `execution/`, `state/`, `runs/ARMED/`, `runs/EXECUTED/`, `runs/CLOSED/`, `runs/KILLED/` | Must not mutate | Computer-only | Live/action state |
| `runs/sentiment/series/*.jsonl` and observed signal series | Must not write or mutate | Computer-only | Observed signal inputs with Computer provenance |
| Sizing, kill-switch decisions, promotion | Forbidden | Computer-only | Computer-authored state transitions |
| Offline validators, schemas, evals, fixtures, RFC/HPR docs | Allowed | Allowed | Non-live PR artifacts; simulated data must be labeled |

## `sal-bot` Research Lane

`sal-bot` may perform public-source research when all of these are true:

1. The purpose is literature, mechanism, OSS, vendor-doc, public-dataset, or implementation research.
2. The research does not call market feeds, broker/account/order APIs, Robinhood, finance connectors,
   scanner APIs, sentiment-signal capture tools, or `pplx_sdk` signal capture.
3. The research does not write or mutate observed signal series, `runs/sentiment/series/*.jsonl`,
   `state/*`, `runs/ARMED/`, `runs/EXECUTED/`, `runs/CLOSED/`, `runs/KILLED/`, or promotion state.
4. The artifact is clearly labeled as research evidence, design rationale, or offline analysis, not an
   observed signal input, live account fact, order instruction, or execution authorization.
5. Provenance is recorded well enough for a reviewer to reconstruct what was learned without relying on
   Slack archaeology.

Examples of allowed outputs:

- a dossier summarizing public papers, vendor docs, OSS APIs, or public datasets;
- an HPR/RFC proposing an artifact contract or eval design;
- code that parses a committed fixture or public schema without fetching live market/account data;
- an offline eval using fake data or committed sanitized Computer artifacts.

## Computer-Only Lane

Computer remains the sole owner of:

- live market data, finance data, broker/account/order APIs, Robinhood, scanners, and execution paths;
- sentiment-signal capture and any writes to observed signal series;
- `execution/`, `state/`, `runs/ARMED/`, `runs/EXECUTED/`, `runs/CLOSED/`, `runs/KILLED/`, and any
  state transition beyond a Teammate-authored proposal;
- sizing, kill-switch decisions, review-before-place, and promotion from `PROPOSED` to `ARMED` to
  `EXECUTED`;
- deciding whether public-source evidence becomes a captured observed signal input.

## Provenance Requirements for `sal-bot` Web Research

Every `sal-bot` research artifact that relies on public web, OSS, vendor docs, or public datasets
should include:

- URL, repository path, dataset name, vendor-doc page, or citation details;
- access timestamp or commit/version where available;
- author/tool identity (`sal-bot`, Computer, human, or other);
- citation, short quote, or committed snapshot when licensing permits;
- clear label: `research_evidence`, `mechanism_prior`, `implementation_reference`, or similar;
- explicit statement that the artifact is not an observed signal input, live account fact, order
  instruction, sizing recommendation, ARMED handoff, or state promotion;
- note of any license, privacy, account, or provenance limitation;
- pointer to Computer-captured artifacts if the evidence later needs observed/live confirmation.

## Denylist for `sal-bot`

`sal-bot` must not:

- use `pplx_sdk` or any credential preset for this proposal;
- use `pplx_sdk.search.web` for observed-series signal capture or use any `pplx_sdk` signal-capture
  preset unless a future accepted rail explicitly authorizes it;
- call live market, finance, sentiment-signal, scanner, account, broker, order, execution, or Robinhood
  APIs;
- run capture scripts that fetch or write observed signal data;
- write or mutate `runs/sentiment/series/*.jsonl` or other observed signal series;
- mutate `execution/`, `state/`, `runs/ARMED/`, `runs/EXECUTED/`, `runs/CLOSED/`, or `runs/KILLED/`;
- size positions, set or override kill-switch decisions, or promote state;
- present public-source research as observed signal data without Computer capture/provenance;
- use Slack prose or tool inventory entries as a substitute for this repo boundary.

## Future SDK Lane

A future owner/Computer decision may grant `sal-bot` a narrower SDK preset for dossier evidence, such
as `academic` or `secgov`. That future lane must be accepted explicitly before use and must say:

- which preset is allowed and which presets remain denied;
- that the lane is for dossier evidence only, not signal capture;
- where citations or snapshots are stored;
- how access time, query, source, and author/tool identity are recorded;
- how validators prevent writes to observed series and live/action state;
- how to revoke the lane if provenance, licensing, or boundary failures occur.

This proposal does not grant that lane.

## Implementation Sequence

1. Land this HPR-style boundary document only.
2. Optionally add a checklist for future research artifacts: source, access timestamp, actor, label,
   denied-surface confirmation, and artifact destination.
3. Optionally add offline validation for PRs that claim `sal-bot` public-source research provenance or
   touch Computer-only paths.
4. Write a separate accepted RFC/HPR before granting any `pplx_sdk` preset to `sal-bot`.
5. Do not implement live connectors, signal capture, SDK usage, scanners, sizing, or state promotion as
   part of this proposal.

## Falsifiable Success Criteria

This proposal succeeds if:

- A future agent can classify a research action as `sal-bot` research, Computer capture, or forbidden
  without reading Slack history.
- `sal-bot` can produce literature/OSS/vendor-doc/public-dataset dossiers with provenance while never
  writing observed signal series or live/action state.
- Computer can continue using its full authorized toolset under Charter rails.
- `reference/CAPABILITY_INVENTORY.md` is understood as an inventory of surfaces, not a blanket grant of
  action authority.
- A public-source research artifact cannot be mistaken for observed signal input, sizing, ARMED state,
  or execution authorization.

Failure modes that should force redesign:

- `sal-bot` uses this document to justify market/account/execution, scanner, signal-capture, Robinhood,
  or `pplx_sdk` signal-capture calls.
- `sal-bot` writes or mutates observed signal series or Computer-owned live/action state.
- Computer's authority is accidentally constrained by rules meant only for `sal-bot`.
- Dossiers lack URL/source, access timestamp, actor identity, or research-vs-signal labels.
- Future SDK access is granted by implication instead of an explicit accepted rail.

## Open Questions

- Should `HANDOFF.md` link to this document after acceptance, or should it remain a reference note
  until a validator/checklist lands?
- Which citation/snapshot format should dossiers use for public-web sources where licenses forbid
  committed raw copies?
- Should public-dataset research evidence live under a new path, or inside each strategy's dossier
  directory?
- Which denylist checks can be enforced mechanically in CI without blocking legitimate Computer-owned
  capture commits?
