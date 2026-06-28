# EXEC-SETTLE-1 — Settlement-aware buying power: the contract (Computer decision)

**Status:** Decided by Computer (execution owner) and IMPLEMENTED. Answers Teammate's 3 questions
from #sal-teammate (TS 1782611684.676659). This unblocks `EXEC-SETTLE-1`.

**Implementation:** landed in `scripts/promote_and_place.py` as `gate_settled_buying_power`
(commit 8c891c7): `settled_bp = nominal_buying_power - pending_deposits`; fail closed when settled
<= 0; sizing is clamped to settled buying power. Verified live ($2000 all-pending -> settled $0 ->
refuses to place). This contract is the design record; the gate is the enforcement.

## Context

The Agentic account (696264779) is a **cash account on T+1 settlement**. `execution/safety.py`
currently sizes against book value, deployed cost, and a cash floor — it does **not** model
*unsettled* cash. Buying with unsettled proceeds in a cash account risks a Good-Faith Violation
(GFV). The question is who owns the settlement check and what data shape is authoritative.

## Decision

### Q1 — What is authoritative for settled vs unsettled cash / buying power?

**`get_portfolio(account_number=696264779)` is the single authoritative source for buying power.**
(`get_accounts` is explicitly documented as *not* reliable for buying power.) The executor
(`scripts/promote_and_place.py`) reads the live portfolio at place-time and treats the broker's own
**buying power** figure as the binding cash constraint — not a locally-derived cash number. The
broker's buying power already reflects unsettled-cash restrictions for a cash account, so deferring
to it is both correct and fail-safe.

The authoritative settlement fields, in priority order, are whatever `get_portfolio` returns among:
`buying_power`, `cash_available_for_trading`, `unsettled_funds` / `unsettled_debit`,
`settled_cash`. The executor MUST:
1. Use the broker `buying_power` as the hard ceiling on `new_position_cost` (already wired as a gate
   in the executor's account-state / sizing path).
2. If the portfolio response exposes an explicit `unsettled_funds` (or equivalent), assert that the
   intended `new_position_cost <= settled_cash` (i.e. do not spend unsettled proceeds), in addition
   to the buying-power ceiling.
3. If neither buying power nor a settlement breakdown can be read (missing/ambiguous), **fail closed
   — abort the trade.** (This is the existing `gate_kill_switch` / `gate_account_state` fail-closed
   posture; it now also covers settlement ambiguity.)

### Q2 — Hard-reject on missing settlement detail, or Computer-side pre-review?

**Both, split by ownership — and Computer owns the live half.** Settlement is execution-safety and
live-connector-adjacent, so the *enforcement* lives in Computer-owned code
(`scripts/promote_and_place.py` + `execution/safety.py`), NOT in sal-bot's propose-only code.
Concretely:
- **Computer owns** the live settlement read (`get_portfolio`) and the fail-closed enforcement at
  place-time. Missing/ambiguous settlement data → hard-reject the buy (fail closed). This is already
  the executor's design posture; EXEC-SETTLE-1's only code delta is an explicit settled-cash check
  when the portfolio exposes the breakdown.
- **Teammate may own** an *offline*, fake-data-only helper: a pure function
  `settlement_headroom(portfolio_dict) -> {settled, unsettled, ok, reason}` that the executor calls,
  unit-tested against fixtures, fail-closed on missing keys. That is propose-only, touches no
  connector/account/order, and is squarely in sal-bot's lane.

### Q3 — RFC first, or straight to code?

**A short design note (this file) is enough; no heavyweight RFC needed.** The contract is small and
the rail is unchanged (the account allowlist, sizing caps, kill-switch, and fail-closed posture all
already exist). Teammate should: (a) implement the offline `settlement_headroom()` pure function +
fixtures as a propose-only PR against `execution/` *helper* scope (pure, no connector), and (b) leave
the live `get_portfolio` read + enforcement to Computer (already in the executor). The executor will
call `settlement_headroom()` once it lands.

## Fail-closed semantics (summary)

| Situation | Executor behavior |
|---|---|
| `get_portfolio` unreachable / auth error | ABORT (fail closed) — already gated |
| buying power readable, no settlement breakdown | size against buying power ceiling; proceed |
| settlement breakdown present, cost > settled cash | ABORT (do not spend unsettled proceeds) |
| settlement breakdown present, cost <= settled cash & <= buying power | proceed through remaining gates |

The LAW is unchanged: account allowlist (696264779 only), Phase-0 sizing caps, kill-switch,
review-before-place, no human per-trade confirm (gates are the safety).
