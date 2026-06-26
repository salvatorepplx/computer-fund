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
- **Signal bus = Slack `#sal-teammate`** — live, bidirectional @-mentions. This is how a trade
  idea or a question PUSHES to the other side. No polling. Teammate posts an ARMED trade alert;
  Computer reads the channel on its execution cron / when pinged and @-mentions back the verdict.
  Both agents are members; each learns the other's Slack user ID from first contact
  and stores it in `state/identities.json`.
- **Durable substrate = this git repo** (`salvatorepplx/computer-fund`) — code, research dossiers,
  knowledge graph, improvement log, ARMED ticket payloads, version history, PRs. The Slack message
  is the nudge + summary; the full structured ticket lives in the repo and is linked from Slack.

State that needs live data (quotes, account, sentiment) is fetched by Computer and committed back
so Teammate can see it. Teammate never fabricates live data it cannot access.

## Directories Teammate owns (proposes via PR or direct commit)
- `sim/`, `research/`, `graph/` logic improvements
- `evals/` — build + sharpen the eval harness (open ticket EVAL-0)
- `corpus/improvement_log.md` — work the open tickets; add new ones
- `runs/` — research write-ups, sim outputs, battle dossiers
- proposes changes to `CONSTITUTION.md` / `CHARTER.md` only via PR (human-confirmed; never self-merge rails)

## Directories Computer owns (Teammate reads, never writes)
- `execution/` (safety rails are LAW), `state/account_*.json`, `state/order_log.jsonl`
- anything that places, sizes, or confirms a real order

## The ARMED handoff (how a trade idea reaches the trader)
1. Teammate researches a battle → runs sim → if it passes falsifiers + the conviction ladder,
   it commits an **ARMED ticket** (`runs/ARMED/<id>.json`, schema below) to the repo.
2. Teammate **@-mentions Computer/Sal in Slack `#sal-teammate`** with a one-line thesis + the repo
   link to the ticket. This is the push — Computer does not poll the repo for signals.
3. Computer (on its cron or when pinged) reads the ticket, fetches LIVE quote + account, runs
   `review_equity_order`, and — if the review passes the Charter rails — **places the order
   autonomously (no human confirm)**. Computer writes `runs/EXECUTED/<id>.json`, moves the ticket
   to `runs/ARMED/consumed/`, and posts the fill to the Slack bus for Teammate (post-trade transparency).
4. If Computer rejects the idea (stale, fails live sizing, bad fill), it writes a `verdict` back
   onto the ticket AND replies in the Slack thread so Teammate learns. Rejections are first-class
   feedback, not failures.

## ARMED ticket schema (`runs/ARMED/<id>.json`)
```json
{
  "id": "battle-RDDT-squeeze-2026-06-26",
  "created_at": "ISO8601",
  "created_by": "teammate",
  "symbol": "RDDT",
  "asset_class": "equity",
  "direction": "bull",
  "thesis_one_liner": "predate retail squeeze before projected sentiment peak",
  "sim": {"edge_score": 0.0, "peak_step": 0, "current_step_est": 0, "predate_window": [0,0]},
  "falsifiers_passed": ["placebo", "date-split", "peer-swap"],
  "proposed_order": {"side":"buy","type":"limit","limit_price":null,"target_pct_of_book":0.15},
  "kill_plan": {"stop_pct": -0.25, "exit_trigger": "at/after projected sentiment peak"},
  "status": "ARMED",
  "verdict": null
}
```
`limit_price` left null = Computer sets it from the live quote at execution time.

## Non-negotiables Teammate must respect
- Never write to `execution/`, never attempt to place/route an order, never touch non-allowlisted accounts.
- Every signal timestamped; simulated sentiment labeled `simulated:true`; no look-ahead.
- Constitution/Charter changes only via PR for human review.
