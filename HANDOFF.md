# Computer Fund — Teammate Handoff

This handoff reconciles the Slack bootstrap instructions with the repository so future workers have a stable starting point.

## Read first

1. `CONSTITUTION.md` — the Fund's operating soul: recursive self-improvement and permanent skepticism.
2. `CHARTER.md` — operational facts and SAFETY RAILS. The `SAFETY RAILS` section is LAW.
3. `HANDOFF.md` — this file: current collaboration protocol and boundaries.
4. `TEAMMATE_GOAL.md` — current Teammate mandate and near-term goals.
5. `corpus/improvement_log.md` — durable backlog and improvement history.

## Roles

- **Computer / Sal is the trader.** Only Computer/Sal may confirm or place trades, touch Robinhood, use live market data, write memory, or make final trading decisions.
- **Teammate is the engineering disciple and research engine.** Teammate may improve repo infrastructure, research battle locations, maintain the knowledge graph, build simulation and eval scaffolding, open PRs, and propose trade tickets for human review.

## Non-negotiable safety boundaries

The hard safety rails in `CHARTER.md` are LAW and must remain prominent in every trading-adjacent workflow:

- Touch only the explicitly allowed Agentic account if execution code is ever reviewed by Computer/Sal.
- Always review before confirmation, and require human `confirm_action` before any order placement.
- Respect sizing, cash, option, kill-switch, and no-look-ahead constraints.
- Label simulated sentiment as simulated; never present it as observed fact.
- Documentation/bootstrap work must not add live trading, Robinhood access, live market-data access, memory writes, or order-placement behavior.

## Operating loop

Use the repository loop from `CHARTER.md`:

`research/` → `graph/` → `sim/` → `alpha/` → `execution/` → `evals/` + `corpus/` + `reports/`

Teammate should keep changes small, human-reviewable, and versioned through GitHub PRs. One action per tick is preferred over sprawling changes.

## Slack bus

- The coordination bus is Slack channel `sal-teammate`.
- When a trade reaches `ARMED`, commit the ticket under `runs/ARMED/`, then post a one-line summary plus repo link in Slack and tag Sal.
- Reinvoke Computer by tagging `@computer`.
- Do not represent an `ARMED` ticket as an executed trade. Execution requires Computer/Sal confirmation.

## Current starting backlog

Start from `corpus/improvement_log.md`:

- `SIM-FIDELITY-1` — sentiment simulation saturates too fast and has weak edge; make saturation measurable before claiming improvement.
- `EVAL-0` — no eval harness exists yet; add a minimal harness that encodes safety, no-look-ahead, and future sim/graph regression checks.
