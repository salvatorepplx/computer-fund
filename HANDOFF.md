# Handoff Contract — Teammate (engineering disciple) ⇄ Computer (the trader)

Two agents, one Fund, sharing this git repo as the only substrate. Neither can do the other's job.

## Roles (fixed)

| | **Teammate** (daemon / disciple) | **Computer** (the trader / the hand) |
|---|---|---|
| Persistence | Always-on heartbeat; never stops | Runs when invoked; stateless + memory-backed |
| Personal connectors | **None** (no Robinhood, no finance data, no user memory) | **All** (Robinhood, finance, memory, assets) |
| Can place trades? | **No — structurally impossible** | **Yes — sole executor, fully autonomous (review-gated, no human confirm)** |
| Owns | Engineering the Fund, wide research, sims, evals, observability, PRs, Tasks | Live market data, execution, confirmation, disclosure, judgment |
| Relationship | Proposes | Disposes |

## Two channels (not one)
- **Machine contract = this git repo** (`salvatorepplx/computer-fund`) — code, research dossiers,
  knowledge graph, improvement log, typed proposal/state artifacts, version history, PRs, and CI/schema
  validation. The repo artifact plus validation result is the source of truth for cross-agent state.
- **Human nudge surface = Slack `#sal-teammate`** — bidirectional @-mentions that point at repo
  artifacts, summarize context, or ask for connector-owned refresh/review. Slack prose is never the
  machine contract: it does not supply required schema fields, override CI, override Charter rails, or
  authorize state transitions.

State that needs live data (quotes, account, sentiment) is fetched by Computer and committed back
so Teammate can see it. Teammate never fabricates live data it cannot access.

Computer-side sentiment refreshes use `scripts/capture_sentiment_tick.py` through the
`FinanceTickerSentimentSource` fetch/normalize seam. The finance sentiment fetch is bounded at 3
attempts per tick with capped 15s/45s backoff for empty, rate-limited, or otherwise no-signal
responses. Failed attempts do not append to the observed JSONL series; if all attempts fail, the
script returns `captured:false` so the missed sample is explicit and retry limits remain finite.

## Directories Teammate owns (proposes via PR or direct commit)
- `sim/`, `research/`, `graph/` logic improvements
- `evals/` — build + sharpen the eval harness (open ticket EVAL-0)
- `corpus/improvement_log.md` — work the open tickets; add new ones
- `runs/` — research write-ups, sim outputs, battle dossiers, and propose-only `runs/PROPOSED/` artifacts
- proposes changes to `CONSTITUTION.md` / `CHARTER.md` only via PR (human-confirmed; never self-merge rails)

## Directories Computer owns (Teammate reads, never writes)
- `execution/` (safety rails are LAW), `state/account_*.json`, `state/order_log.jsonl`
- `runs/ARMED/`, `runs/EXECUTED/`, `runs/CLOSED/`, `runs/KILLED/`
- anything that promotes a proposal, places, sizes, reviews, or confirms a real order

## The PROPOSED handoff (how a trade idea reaches the trader)
1. Teammate researches a battle → runs sim → if it passes falsifiers + the conviction ladder,
   it commits a **PROPOSED artifact** (`runs/PROPOSED/<id>.json`, shape below) to the repo. This
   artifact is offline/propose-only and must be incapable of placing or implying an order.
   Computer may also write `writer=computer` PROPOSED artifacts from its own alpha pipeline; these
   remain propose-only until Computer separately promotes them after Charter review.
2. Teammate may **@-mention Computer/Sal in Slack `#sal-teammate`** with a one-line thesis + the repo
   link to the proposal. This is only a human nudge/pointer; the typed repo artifact and CI/schema
   validation are the machine-readable contract.
3. Computer reads a validated proposal, fetches live connector-backed inputs (quotes, account state,
   sentiment refreshes, broker/order context), runs the required Charter review gates, and decides
   whether to promote it.
4. Only Computer may promote `PROPOSED -> ARMED -> EXECUTED -> CLOSED/KILLED`. `runs/ARMED/<id>.json`
   is the first state that may contain execution intent, sizing, or order-review output, and it must be
   Computer-authored after live review under the Charter rails.
5. If Computer rejects or kills the idea (stale, fails live sizing, bad fill, needs more data), it writes
   the Computer-owned verdict/outcome artifact and may reply in Slack so Teammate learns. Rejections are
   first-class feedback, not failures.

## PROPOSED artifact shape (`runs/PROPOSED/<id>.json`)
```json
{
  "schema_version": "cf.integration.v1",
  "artifact_id": "battle-RDDT-squeeze-2026-06-26",
  "artifact_type": "proposal",
  "state": "PROPOSED",
  "created_at": "2026-06-26T19:30:00Z",
  "writer": "teammate",
  "owner": "computer",
  "simulated": true,
  "provenance": {
    "inputs": ["runs/research/battle-RDDT-squeeze.md", "runs/evals/battle-RDDT-squeeze.json"],
    "raw_ref_explanation": "Teammate proposal has no connector raw backing; Computer must fetch live inputs."
  },
  "validation": {
    "required_checks": ["schema", "charter", "ownership", "transition"],
    "passed_checks": []
  },
  "payload": {
    "thesis": "predate retail squeeze before projected sentiment peak",
    "entities": ["TICKER:RDDT"],
    "dossier_refs": ["runs/research/battle-RDDT-squeeze.md"],
    "offline_eval_refs": ["runs/evals/battle-RDDT-squeeze.json"],
    "requested_live_checks": ["quote_snapshot", "account_safety_review", "sentiment_capture_refresh"],
    "non_authorizations": ["no_order", "no_sizing", "no_execution_instruction"],
    "open_risks": ["Computer must verify live price, account, sizing caps, and kill-switch status."]
  }
}
```
The reviewer-facing schema is `schemas/proposed.schema.json`; the authoritative offline validator is
`evals/proposed_validator.py`; run it with `env -u PYTHONPATH python -m evals.proposed_validator
runs/PROPOSED`. The schema has writer-specific profiles for Teammate offline proposals and Computer
alpha-pipeline proposals. Any proposal may ask for live checks, but it must not include proposed order
fields, target sizing, broker/account data, or any wording that authorizes execution.

## Non-negotiables Teammate must respect
- Never write to `execution/`, create or edit `runs/ARMED/` handoffs, promote state, attempt to
  place/route an order, review an order, size a position, touch Robinhood/live market/account/order/
  execution APIs, or touch non-allowlisted accounts.
- Every signal timestamped; simulated sentiment labeled `simulated:true`; no look-ahead.
- Constitution/Charter changes only via PR for human review.
