#!/usr/bin/env python3
"""Computer Fund — PROPOSED -> ARMED -> PLACE executor (Blocker B).

The pipeline (execution/alpha_pipeline.py) writes PROPOSED artifacts but is
*propose-only* and structurally incapable of placing orders. This script is the
missing entrypoint that promotes a validated PROPOSED artifact through the CHARTER
review gates and, only when every gate passes, places a real order autonomously.

DESIGN: FAIL CLOSED. Every gate aborts on ambiguity. The review gates ARE the
safety (no human per-trade confirm, per CHARTER §2 + the operating doctrine).

GATE ORDER (all must pass; any failure aborts and writes nothing to ARMED/EXECUTED):
  0. Artifact loads + passes evals/proposed_validator (strict schema + ISO8601 + non-auth).
  1. Eligibility re-confirm: provenance verdict==EDGE, circular==False,
     permutation.significant_at_0.10==True.
  2. PRICE-AXIS QUALITY gate (lesson 2026-06-28, RDDT kill): the observed series the
     edge rides must be non-degenerate (>=15 distinct prices, <20% zero returns, no
     multi-hour capture gap) — a permutation null is blind to a corrupted price axis,
     so we check it here explicitly, ahead of trusting the edge.
  3. Account allowlist (CHARTER §1): 696264779 ONLY; Roth/margin abort. assert_account_allowed.
  4. Live account state (connector): get_accounts -> account present + agentic_allowed.
  5. Kill-switch (CHARTER §4): get_portfolio -> book/HWM; kill_check; circuit breaker
     must NOT be tripped (no new entries while tripped).
  6. Live quote (connector): get_equity_quotes -> a real price (not the corpus proxy).
  7. Sizing (CHARTER §3): Phase-0 caps via safety.build_ticket (raises on any violation).
  8. review_equity_order (connector): no blocking pre-trade alert (buying power, halt, PDT).
  9. Write runs/ARMED/.
 10. PLACE (only with --place): place_equity_order with the ticket ref_id (idempotent).
 11. Log fill -> state/order_log.jsonl + runs/EXECUTED/.

USAGE:
  python scripts/promote_and_place.py runs/PROPOSED/<artifact>.json              # dry-run (default): gates + ARMED, NO place
  python scripts/promote_and_place.py runs/PROPOSED/<artifact>.json --place      # real order (autonomous, gates ARE the safety)

Connector calls go through the `external-tool` CLI (api_credentials=["external-tools"]).
A connector 401/auth error is treated as a BLOCKING gate failure (fail closed) — we never
place against an unauthenticated/ambiguous account state.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from execution import safety
from execution.safety import SafetyViolation
from evals.proposed_validator import validate_proposed_file
from execution.ingest_runner import load_series

ACCOUNT = "696264779"          # CHARTER §1 — the ONLY tradeable account
SOURCE_ID = "robinhood"
ARMED_DIR = ROOT / "runs" / "ARMED"
EXECUTED_DIR = ROOT / "runs" / "EXECUTED"
STATE_DIR = ROOT / "state"

# Price-axis quality thresholds (lesson 2026-06-28, RDDT kill).
MIN_DISTINCT_PRICES = 15
MAX_ZERO_RETURN_FRAC = 0.20
MAX_CAPTURE_GAP_HOURS = 3.0


class GateFail(Exception):
    """A review gate failed; abort fail-closed. Never reaches place."""


def _utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def call_tool(tool_name: str, arguments: dict) -> dict:
    """Call a connected tool via the external-tool CLI. Fail closed on any error."""
    payload = json.dumps({"source_id": SOURCE_ID, "tool_name": tool_name, "arguments": arguments})
    proc = subprocess.run(["external-tool", "call", payload], capture_output=True, text=True)
    if proc.returncode != 0:
        raise GateFail(f"connector {tool_name} CLI error (rc={proc.returncode}): {proc.stderr.strip()[:300]}")
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise GateFail(f"connector {tool_name} returned non-JSON: {proc.stdout.strip()[:200]}")
    # connectors signal auth/errors in-band
    if isinstance(out, dict) and (out.get("error") or out.get("status") in (401, 403)):
        raise GateFail(f"connector {tool_name} auth/error (fail closed): {str(out.get('error'))[:200]} status={out.get('status')}")
    return out


# ---- GATE 0: artifact validity ------------------------------------------------
def gate_validate_artifact(path: Path) -> dict:
    if not path.exists():
        raise GateFail(f"artifact does not exist: {path}")
    issues = validate_proposed_file(path)
    if issues:
        raise GateFail("artifact fails proposed_validator:\n- " + "\n- ".join(f"{i.path}: {i.message}" for i in issues))
    art = json.loads(path.read_text())
    if art.get("state") != "PROPOSED":
        raise GateFail(f"artifact state is {art.get('state')!r}, expected PROPOSED")
    return art


# ---- GATE 1: eligibility re-confirm -------------------------------------------
def gate_eligibility(art: dict) -> dict:
    payload = art.get("payload", {})
    prov = payload.get("signal_provenance", {})
    if prov.get("verdict") != "EDGE":
        raise GateFail(f"provenance verdict is {prov.get('verdict')!r}, not EDGE")
    if prov.get("circular") is not False:
        raise GateFail(f"provenance circular flag is {prov.get('circular')!r}, must be False")
    perm = prov.get("permutation") or {}
    if not perm.get("significant_at_0.10"):
        raise GateFail("permutation not significant at 0.10 (or missing from artifact) — the trade gate requires permutation p<=0.10")
    entities = payload.get("entities") or []
    if len(entities) != 1 or not str(entities[0]).startswith("TICKER:"):
        raise GateFail(f"expected exactly one TICKER: entity, got {entities!r}")
    return {"entity": entities[0], "symbol": entities[0].split(":")[-1], "best_lag": prov.get("best_lag"),
            "best_corr": prov.get("best_corr"), "perm_p": perm.get("p_value")}


# ---- GATE 2: price-axis quality (the RDDT lesson) -----------------------------
def gate_price_axis_quality(entity: str) -> dict:
    rows = load_series(entity)
    prices = [r.get("price_proxy") for r in rows if isinstance(r.get("price_proxy"), (int, float))]
    if len(prices) < 3:
        raise GateFail(f"price axis: <3 usable price points ({len(prices)})")
    distinct = len(set(round(p, 4) for p in prices))
    rets = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    zero_frac = sum(1 for r in rets if abs(r) < 1e-9) / len(rets) if rets else 1.0
    # capture-gap check
    def _ts(r):
        t = r.get("captured_at") or r.get("ts") or ""
        try:
            return dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
        except Exception:
            return None
    times = [t for t in (_ts(r) for r in rows) if t is not None]
    max_gap_h = 0.0
    for i in range(1, len(times)):
        gap = (times[i] - times[i-1]).total_seconds() / 3600.0
        max_gap_h = max(max_gap_h, gap)
    report = {"distinct_prices": distinct, "zero_return_frac": round(zero_frac, 3),
              "max_capture_gap_h": round(max_gap_h, 2), "n_prices": len(prices)}
    fails = []
    if distinct < MIN_DISTINCT_PRICES:
        fails.append(f"only {distinct} distinct prices (need >= {MIN_DISTINCT_PRICES}) — degenerate price axis")
    if zero_frac > MAX_ZERO_RETURN_FRAC:
        fails.append(f"zero-return fraction {zero_frac:.0%} > {MAX_ZERO_RETURN_FRAC:.0%} — stuck/boilerplate quotes")
    if max_gap_h > MAX_CAPTURE_GAP_HOURS:
        fails.append(f"max capture gap {max_gap_h:.1f}h > {MAX_CAPTURE_GAP_HOURS}h")
    if fails:
        raise GateFail("price-axis quality (a permutation null is blind to this):\n- " + "\n- ".join(fails) + f"\n  report={report}")
    return report


# ---- GATE 3: account allowlist ------------------------------------------------
def gate_account_allowlist() -> None:
    safety.assert_account_allowed(ACCOUNT)  # raises SafetyViolation on Roth/margin/unknown


# ---- GATE 4: live account state ----------------------------------------------
def gate_account_state() -> dict:
    accts = call_tool("get_accounts", {})
    arr = accts.get("accounts") if isinstance(accts, dict) else accts
    if not isinstance(arr, list):
        raise GateFail(f"get_accounts unexpected shape: {str(accts)[:200]}")
    match = next((a for a in arr if str(a.get("account_number")) == ACCOUNT), None)
    if not match:
        raise GateFail(f"account {ACCOUNT} not found in get_accounts")
    if match.get("agentic_allowed") is False:
        raise GateFail(f"account {ACCOUNT} is not agentic_allowed")
    return match


# ---- GATE 5: kill-switch ------------------------------------------------------
def gate_kill_switch() -> dict:
    port = call_tool("get_portfolio", {"account_number": ACCOUNT})
    book = None
    for k in ("total_value", "total_market_value", "market_value", "equity", "portfolio_value"):
        v = port.get(k) if isinstance(port, dict) else None
        if v is not None:
            try:
                book = float(v); break
            except (TypeError, ValueError):
                pass
    if book is None or book <= 0:
        raise GateFail(f"could not read a positive book value from get_portfolio: {str(port)[:200]}")
    hwm_path = STATE_DIR / "high_water_mark.json"
    hwm = book
    if hwm_path.exists():
        try:
            hwm = float(json.loads(hwm_path.read_text()).get("hwm", book))
        except Exception:
            hwm = book
    ks = safety.kill_check([], book, hwm)
    if ks["circuit_breaker_tripped"] or not ks["new_entries_allowed"]:
        raise GateFail(f"kill-switch: circuit breaker tripped (book_dd={ks['book_drawdown']}); no new entries")
    return {"book_value": book, "hwm": hwm, "_portfolio": port, **ks}


# ---- GATE 5b: settled buying power (EXEC-SETTLE-1) ----------------------------
# The Agentic account is a CASH account with T+1 settlement (CHARTER §5). Trading on
# UNSETTLED funds in a cash account risks a good-faith / free-riding violation. The
# broker's nominal buying_power can include pending_deposits / unsettled proceeds, so
# we compute a fail-closed SETTLED buying power and size against THAT, never nominal.
# This is Computer-owned (live connector at promotion time), the answer to Teammate's
# EXEC-SETTLE-1: settlement-awareness lives here in the executor, not in offline safety.py.
def gate_settled_buying_power(portfolio: dict | None = None) -> dict:
    port = portfolio if portfolio is not None else call_tool("get_portfolio", {"account_number": ACCOUNT})
    if not isinstance(port, dict):
        raise GateFail(f"get_portfolio unexpected shape for settlement check: {str(port)[:200]}")

    def _num(*path, default=None):
        cur = port
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return default
        try:
            return float(cur)
        except (TypeError, ValueError):
            return default

    nominal_bp = _num("buying_power", "buying_power")
    if nominal_bp is None:
        nominal_bp = _num("buying_power")  # flat shape fallback
    cash = _num("cash")
    pending = _num("pending_deposits", default=0.0) or 0.0
    # Authoritative SETTLED buying power = nominal buying power minus anything that is
    # demonstrably unsettled (pending deposits). Fail closed if we cannot determine it.
    if nominal_bp is None:
        raise GateFail("settlement: buying_power missing from get_portfolio (fail closed).")
    settled_bp = nominal_bp - pending
    info = {
        "nominal_buying_power": nominal_bp, "cash": cash,
        "pending_deposits": pending, "settled_buying_power": round(settled_bp, 2),
    }
    if settled_bp <= 0:
        raise GateFail(
            f"settlement: settled buying power ${settled_bp:,.2f} <= 0 "
            f"(nominal ${nominal_bp:,.2f} is unsettled: pending_deposits ${pending:,.2f}). "
            f"Cash account T+1 — cannot trade on unsettled funds. {info}")
    return info


# ---- GATE 6: live quote -------------------------------------------------------
def gate_live_quote(symbol: str) -> float:
    q = call_tool("get_equity_quotes", {"symbols": [symbol]})
    quotes = q.get("quotes") if isinstance(q, dict) else q
    if not isinstance(quotes, list) or not quotes:
        raise GateFail(f"get_equity_quotes returned no quote for {symbol}: {str(q)[:200]}")
    row = quotes[0]
    for k in ("last_trade_price", "last_extended_hours_trade_price", "ask_price", "price"):
        v = row.get(k)
        if v is not None:
            try:
                px = float(v)
                if px > 0:
                    return px
            except (TypeError, ValueError):
                pass
    raise GateFail(f"no usable live price for {symbol} in {str(row)[:200]}")


# ---- GATE 7+8: sizing + review ------------------------------------------------
def gate_size_and_review(symbol: str, book_value: float, live_price: float, rationale: str,
                        settled_bp: float | None = None) -> tuple:
    # Phase-0 sizing: target the single-position cap, conservative. Whole shares only.
    # Clamp to SETTLED buying power (EXEC-SETTLE-1): never size above funds that have settled.
    target_cost = safety.MAX_SINGLE_POS_FRAC * book_value
    if settled_bp is not None:
        target_cost = min(target_cost, settled_bp)
    qty = int(target_cost // live_price)
    if qty < 1:
        raise GateFail(f"sizing: affordable cap ${target_cost:,.2f} at ${live_price:,.2f}/sh => 0 shares "
                       f"(single-pos cap ${safety.MAX_SINGLE_POS_FRAC*book_value:,.2f}, "
                       f"settled BP {('$%.2f' % settled_bp) if settled_bp is not None else 'n/a'}); "
                       f"position too small to place")
    new_position_cost = qty * live_price
    # build_ticket validates allowlist + sizing (raises SafetyViolation on any cap breach)
    ticket = safety.build_ticket(
        account_number=ACCOUNT, symbol=symbol, side="buy", type="market",
        book_value=book_value, deployed_cost=0.0, new_position_cost=new_position_cost,
        asset_class="equity", quantity=str(qty), time_in_force="gfd",
        market_hours="regular_hours", rationale=rationale,
    )
    # review_equity_order — pre-trade alerts gate
    review = call_tool("review_equity_order", {
        "account_number": ACCOUNT, "symbol": symbol, "side": "buy",
        "type": "market", "quantity": str(qty), "market_hours": "regular_hours",
    })
    alerts = review.get("alerts") or review.get("pre_trade_alerts") or []
    blocking = [a for a in alerts if (isinstance(a, dict) and a.get("blocking")) or (isinstance(a, str))]
    if blocking:
        raise GateFail(f"review_equity_order blocking alerts: {blocking}")
    return ticket, qty, new_position_cost, review


def write_armed(art_path: Path, art: dict, gates: dict, ticket) -> Path:
    ARMED_DIR.mkdir(parents=True, exist_ok=True)
    armed = dict(art)
    armed["state"] = "ARMED"
    armed["armed"] = {
        "armed_at": _utcnow(), "armed_by": "computer",
        "account_number": ACCOUNT, "ref_id": ticket.ref_id,
        "gates": gates, "ticket": {
            "symbol": ticket.symbol, "side": ticket.side, "type": ticket.type,
            "quantity": ticket.quantity, "market_hours": ticket.market_hours,
        },
        "note": "All CHARTER review gates passed. Sizing under Phase-0 caps. Place is autonomous (no human confirm); gates ARE the safety.",
    }
    out = ARMED_DIR / art_path.name
    out.write_text(json.dumps(armed, indent=2))
    return out


def place_and_log(ticket, gates: dict) -> dict:
    place_args = ticket.to_place_args()
    placed = call_tool("place_equity_order", place_args)
    order_id = placed.get("id") or placed.get("order_id") if isinstance(placed, dict) else None
    # log to order_log.jsonl
    ticket.status = "PLACED"
    safety.log_ticket(ticket)
    # EXECUTED artifact
    EXECUTED_DIR.mkdir(parents=True, exist_ok=True)
    rec = {"executed_at": _utcnow(), "ref_id": ticket.ref_id, "order_id": order_id,
           "account_number": ACCOUNT, "symbol": ticket.symbol, "side": ticket.side,
           "quantity": ticket.quantity, "place_response": placed, "gates": gates}
    (EXECUTED_DIR / f"{ticket.symbol}-{ticket.ref_id[:8]}.json").write_text(json.dumps(rec, indent=2))
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description="Promote a validated PROPOSED artifact to ARMED and (optionally) place.")
    ap.add_argument("artifact", help="path to runs/PROPOSED/<artifact>.json")
    ap.add_argument("--place", action="store_true",
                    help="actually place the order (default: dry-run = gates + ARMED only, NO order).")
    a = ap.parse_args()
    art_path = (ROOT / a.artifact) if not Path(a.artifact).is_absolute() else Path(a.artifact)

    print(f"=== promote_and_place: {art_path.name} (mode={'PLACE' if a.place else 'DRY-RUN'}) ===")
    try:
        art = gate_validate_artifact(art_path);                       print("GATE 0 artifact-valid: PASS")
        elig = gate_eligibility(art);                                  print(f"GATE 1 eligibility: PASS ({elig['symbol']} lag={elig['best_lag']} corr={elig['best_corr']} p={elig['perm_p']})")
        pxq = gate_price_axis_quality(elig["entity"]);                print(f"GATE 2 price-axis-quality: PASS ({pxq})")
        gate_account_allowlist();                                     print(f"GATE 3 account-allowlist: PASS ({ACCOUNT})")
        acct = gate_account_state();                                  print("GATE 4 account-state: PASS (agentic_allowed)")
        ks = gate_kill_switch();                                       print(f"GATE 5 kill-switch: PASS (book=${ks['book_value']:,.2f} dd={ks['book_drawdown']})")
        settle = gate_settled_buying_power(ks.get("_portfolio")); print(f"GATE 5b settled-buying-power: PASS (settled=${settle['settled_buying_power']:,.2f} of nominal ${settle['nominal_buying_power']:,.2f}; pending ${settle['pending_deposits']:,.2f})")
        live_px = gate_live_quote(elig["symbol"]);                    print(f"GATE 6 live-quote: PASS (${live_px:,.2f})")
        rationale = f"RDDT-class lead-lag PROPOSED {art_path.name}: lag={elig['best_lag']} corr={elig['best_corr']} perm_p={elig['perm_p']}"
        ticket, qty, cost, review = gate_size_and_review(elig["symbol"], ks["book_value"], live_px, rationale, settled_bp=settle["settled_buying_power"])
        print(f"GATE 7 sizing: PASS ({qty} sh ~${cost:,.2f}, <= {safety.MAX_SINGLE_POS_FRAC:.0%} cap, settled-clamped)")
        print("GATE 8 review-order: PASS (no blocking alerts)")
        gates = {"eligibility": elig, "price_axis": pxq, "kill_switch": {k: v for k, v in ks.items() if k != '_portfolio'},
                 "settlement": settle, "live_price": live_px, "qty": qty, "est_cost": round(cost, 2)}
        armed_path = write_armed(art_path, art, gates, ticket)
        print(f"GATE 9 ARMED written: {armed_path.relative_to(ROOT)}  (ref_id={ticket.ref_id})")
    except (GateFail, SafetyViolation) as e:
        print(f"\nABORTED (fail-closed) — no order placed, nothing armed past the failing gate:\n  {e}")
        return 2

    if not a.place:
        print("\nDRY-RUN complete: all gates passed and ARMED written. NOT placing (pass --place to place autonomously).")
        return 0

    print("\n--place set: all gates passed -> placing autonomously (gates ARE the safety)...")
    try:
        rec = place_and_log(ticket, gates)
        print(f"PLACED: order_id={rec['order_id']} ref_id={rec['ref_id']} -> state/order_log.jsonl + runs/EXECUTED/")
        print(f"BUS: ARMED+PLACED {ticket.symbol} {qty}sh market @~${live_px:,.2f} (acct ••{ACCOUNT[-4:]}, Phase-0)")
        return 0
    except (GateFail, SafetyViolation) as e:
        print(f"PLACE failed after arming (no fill logged): {e}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
