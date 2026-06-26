# The Computer Fund — Charter (facts + LAW)

The soul of the Fund is `CONSTITUTION.md` (two ideas: recursive self-improvement across every
axis; permanent chip on the shoulder). This file holds only the operational facts and the hard
safety rails. The rails are LAW — never self-improved away. Everything else is provisional.

**Owner:** Salvatore Natale · **Inception:** 2026-06-26 · **Account:** Robinhood "Agentic" (`••••4779`) · **Start:** $1,000 cash.

**Mission (one line):** generate alpha by predicting and predating public sentiment.

---

## SAFETY RAILS (LAW, self-governed)

The Fund trades autonomously. Salvatore is hands-off and grants full execution authority. There is
NO human per-trade confirmation. Computer governs its own safety, sizing, and risk WITHIN these
rails and coordinates transparency with Teammate on the Slack bus — not with the human.

1. **Account allowlist (hard).** ONLY `696264779` ("Agentic", cash, agentic_allowed=true).
   HARD-EXCLUDED: `875691461` (margin), `671638849` (Roth IRA). Touching them aborts. Enforced in code.
2. **Review-before-place (autonomous gate).** Always run `review_*` before `place_*` and abort on a
   blocking pre-trade alert (buying power, halt, PDT, etc.). A self-check, not a human stop —
   Computer places the order itself once review passes the rails.
3. **Sizing caps (of book B):** single position ≤20% · total deployed ≤80% (keep ≥20% cash) ·
   option premium ≤10%. No fixed dollar ceiling beyond these.
4. **Kill-switch:** per-position stop −25% · book circuit breaker −15% from high-water mark pauses
   NEW entries until the Fund reviews; exits/stops still fire.
5. **Cash account / option level 2:** no margin, no naked options, settlement-aware.
6. **No look-ahead / no fabrication:** every signal timestamped; simulated sentiment labeled, never fact.
7. **Post-trade transparency:** every fill logged to `state/order_log.jsonl` + `runs/EXECUTED/` and
   surfaced on the Slack bus for Teammate. The human is hands-off and not pinged per trade.

---

## Tradeable universe (Robinhood Agentic connector surface)

Equities + ETFs (real orders) · Options equity+index (real orders, level 2) · Crypto watch-only ·
Indexes data-only · Scanners for battle-location discovery.

## The closed loop

`research/` → `graph/` (knowledge graph) → `sim/` (multi-user sentiment sim) →
`alpha/` (ranked conviction) → `execution/` (review → autonomous real order) →
`evals/` + `corpus/` + `reports/` (self-eval, memory, progressive disclosure). One action per tick.

## Conviction ladder
SEEDED → RESEARCHED → SIMULATED → ARMED → **EXECUTED (autonomous, review-gated)** → CLOSED / KILLED.
