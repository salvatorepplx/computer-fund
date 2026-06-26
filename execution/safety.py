"""
Computer Fund — execution safety rails (LAW).

This module is the single chokepoint every proposed trade MUST pass through.
It does NOT place orders itself (the broker connector does that via the agent).
It validates a proposed order against the Charter's hard rules and produces a
reviewed, human-confirmable order ticket. Any violation raises SafetyViolation.

Design: fail closed. If anything is ambiguous, abort.
"""
from __future__ import annotations
import json, uuid, datetime as dt
from dataclasses import dataclass, asdict
from pathlib import Path

# ---- LAW: account allowlist (Charter §1) -----------------------------------
ALLOWED_ACCOUNTS = {"696264779"}          # "Agentic" cash account ONLY
HARD_EXCLUDED = {"875691461", "671638849"}  # margin individual, Roth IRA

# ---- LAW: sizing caps (Charter §3) -----------------------------------------
MAX_SINGLE_POS_FRAC = 0.20    # ≤20% of book at entry
MAX_TOTAL_DEPLOYED_FRAC = 0.80  # ≥20% cash always
MAX_OPTION_PREMIUM_FRAC = 0.10  # ≤10% of book in option premium

# ---- LAW: kill-switch (Charter §4) -----------------------------------------
PER_POSITION_STOP = -0.25     # -25% unrealized hard stop
BOOK_CIRCUIT_BREAKER = -0.15  # -15% from HWM pauses new entries

STATE_DIR = Path(__file__).resolve().parent.parent / "state"


class SafetyViolation(Exception):
    pass


@dataclass
class OrderTicket:
    ref_id: str
    account_number: str
    symbol: str
    side: str           # buy | sell
    type: str           # market | limit | stop_market | stop_limit
    quantity: str | None
    dollar_amount: str | None
    limit_price: str | None
    stop_price: str | None
    time_in_force: str
    market_hours: str
    asset_class: str    # equity | option
    rationale: str
    created_at: str
    status: str = "PROPOSED"   # PROPOSED -> REVIEWED -> CONFIRMED -> PLACED | ABORTED

    def to_place_args(self) -> dict:
        """Args for place_equity_order (drops None + meta fields)."""
        d = {
            "account_number": self.account_number,
            "symbol": self.symbol,
            "side": self.side,
            "type": self.type,
            "time_in_force": self.time_in_force,
            "market_hours": self.market_hours,
            "ref_id": self.ref_id,
        }
        for k in ("quantity", "dollar_amount", "limit_price", "stop_price"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        return d


def assert_account_allowed(account_number: str) -> None:
    """Charter §1. Fail closed."""
    acct = str(account_number).strip()
    if acct in HARD_EXCLUDED:
        raise SafetyViolation(
            f"REFUSED: account {acct[-4:].rjust(4,'•')} is HARD-EXCLUDED "
            f"(Roth IRA / margin). The Fund may only trade the Agentic account."
        )
    if acct not in ALLOWED_ACCOUNTS:
        raise SafetyViolation(
            f"REFUSED: account ending {acct[-4:]} is not on the allowlist. "
            f"Only {sorted(ALLOWED_ACCOUNTS)} is permitted."
        )


def check_sizing(book_value: float, deployed_cost: float,
                 new_position_cost: float, asset_class: str,
                 option_premium_at_risk: float = 0.0) -> list[str]:
    """Charter §3. Returns list of violation strings (empty = OK)."""
    v = []
    if book_value <= 0:
        return ["REFUSED: book value is zero/unknown — cannot size."]
    if new_position_cost > MAX_SINGLE_POS_FRAC * book_value + 1e-9:
        v.append(
            f"Single-position cap: ${new_position_cost:,.2f} exceeds "
            f"{MAX_SINGLE_POS_FRAC:.0%} of ${book_value:,.2f} "
            f"(${MAX_SINGLE_POS_FRAC*book_value:,.2f}).")
    if deployed_cost + new_position_cost > MAX_TOTAL_DEPLOYED_FRAC * book_value + 1e-9:
        v.append(
            f"Total-deployed cap: ${deployed_cost + new_position_cost:,.2f} "
            f"exceeds {MAX_TOTAL_DEPLOYED_FRAC:.0%} of book "
            f"(${MAX_TOTAL_DEPLOYED_FRAC*book_value:,.2f}); must keep ≥20% cash.")
    if asset_class == "option" and option_premium_at_risk > MAX_OPTION_PREMIUM_FRAC * book_value + 1e-9:
        v.append(
            f"Option-premium cap: ${option_premium_at_risk:,.2f} exceeds "
            f"{MAX_OPTION_PREMIUM_FRAC:.0%} of book.")
    return v


def kill_check(positions: list[dict], book_value: float, hwm: float) -> dict:
    """Charter §4. positions: [{symbol, unrealized_pct}], returns actions."""
    breaches = [p for p in positions if p.get("unrealized_pct", 0) <= PER_POSITION_STOP]
    book_dd = (book_value / hwm - 1.0) if hwm > 0 else 0.0
    return {
        "position_stops": [p["symbol"] for p in breaches],
        "book_drawdown": round(book_dd, 4),
        "circuit_breaker_tripped": book_dd <= BOOK_CIRCUIT_BREAKER,
        "new_entries_allowed": book_dd > BOOK_CIRCUIT_BREAKER,
    }


def build_ticket(account_number: str, symbol: str, side: str, type: str,
                 book_value: float, deployed_cost: float, new_position_cost: float,
                 asset_class: str = "equity", quantity: str | None = None,
                 dollar_amount: str | None = None, limit_price: str | None = None,
                 stop_price: str | None = None, time_in_force: str = "gfd",
                 market_hours: str = "regular_hours", rationale: str = "",
                 option_premium_at_risk: float = 0.0) -> OrderTicket:
    """Validate everything, then emit a PROPOSED ticket. Raises on any violation."""
    assert_account_allowed(account_number)
    if side == "buy":
        viol = check_sizing(book_value, deployed_cost, new_position_cost,
                            asset_class, option_premium_at_risk)
        if viol:
            raise SafetyViolation("Sizing violations:\n- " + "\n- ".join(viol))
    return OrderTicket(
        ref_id=str(uuid.uuid4()),
        account_number=str(account_number),
        symbol=symbol, side=side, type=type,
        quantity=quantity, dollar_amount=dollar_amount,
        limit_price=limit_price, stop_price=stop_price,
        time_in_force=time_in_force, market_hours=market_hours,
        asset_class=asset_class, rationale=rationale,
        created_at=dt.datetime.utcnow().isoformat() + "Z",
    )


def log_ticket(ticket: OrderTicket) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    log = STATE_DIR / "order_log.jsonl"
    with log.open("a") as f:
        f.write(json.dumps(asdict(ticket)) + "\n")
    return log


if __name__ == "__main__":
    # self-test: the rails must reject the Roth IRA and oversized positions.
    print("Self-test: safety rails")
    for acct in ("671638849", "875691461", "999999999"):
        try:
            assert_account_allowed(acct); print(f"  FAIL: {acct} allowed")
        except SafetyViolation as e:
            print(f"  OK refused {acct[-4:]}: {str(e)[:60]}...")
    assert_account_allowed("696264779"); print("  OK allowed Agentic 4779")
    v = check_sizing(1000, 0, 300, "equity")
    print(f"  $300 on $1000 book -> {'REJECTED' if v else 'ok'} (expect REJECTED >20%)")
    v = check_sizing(1000, 0, 150, "equity")
    print(f"  $150 on $1000 book -> {'rejected' if v else 'OK'} (expect OK)")
    print("Self-test done.")
