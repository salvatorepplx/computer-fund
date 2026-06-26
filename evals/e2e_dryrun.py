"""
End-to-end DRY-RUN of the full Computer Fund chain, with a SYNTHETIC authoritative
EDGE so we prove the path works before any live data depends on it. Places NOTHING.

Chain exercised:
  synthetic EDGE verdict
   -> alpha_pipeline.conviction_from_verdict        (ranking)
   -> alpha_pipeline.write_proposed                 (PROPOSE-ONLY artifact, schema-checked)
   -> [promotion step, Computer-side] read proposal, attach live-ish inputs
   -> safety.assert_account_allowed                 (Charter §1 allowlist — must REJECT Roth/margin)
   -> safety.check_sizing                           (Charter §3 caps — must REJECT oversize)
   -> safety.build_ticket                           (emits PROPOSED OrderTicket, still not placed)
   -> safety.kill_check                             (Charter §4 — block entries if circuit tripped)

Asserts the rails FIRE (negative tests) and the happy path PRODUCES a ticket (positive test).
"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from execution import safety
from execution.alpha_pipeline import conviction_from_verdict, write_proposed

PASS, FAIL = "PASS", "FAIL"
results = []

def check(name, cond):
    results.append((name, PASS if cond else FAIL))
    print(f"  [{PASS if cond else FAIL}] {name}")

# ---- 1) synthetic authoritative non-circular EDGE --------------------------
edge = {"entity": "TICKER:NVDA", "verdict": "EDGE", "authoritative": True,
        "circularity_flag": False, "best_corr": 0.71, "best_lag": 2,
        "n": 26, "min_n": 24, "contemp_corr": 0.25,
        "all_lags": [{"lag": -2, "corr": 0.1}, {"lag": -1, "corr": 0.15},
                     {"lag": 0, "corr": 0.2}, {"lag": 1, "corr": 0.55},
                     {"lag": 2, "corr": 0.71}]}
sent = {"score": 0.42, "confidence": 0.95}

print("STEP 1: conviction from synthetic EDGE")
c = conviction_from_verdict(edge, sent)
check("eligible EDGE accepted", c["eligible"] and c["conviction"] > 0)
print(f"        conviction={c['conviction']} components={c['components']}")

print("STEP 2: write PROPOSE-ONLY artifact + schema/non-authorization checks")
path = write_proposed("TICKER:NVDA", c)
art = json.loads((ROOT / path).read_text())
check("schema_version cf.integration.v1", art["schema_version"] == "cf.integration.v1")
check("state==PROPOSED", art["state"] == "PROPOSED")
pay = art["payload"]
# critical: proposal must NOT contain any order/sizing/exec fields
forbidden = {"order", "quantity", "side", "limit_price", "sizing", "account_number", "dollar_amount"}
check("no order/sizing/exec fields in proposal", not (forbidden & set(pay.keys())))
check("non_authorizations present", set(pay["non_authorizations"]) >= {"no_order", "no_sizing", "no_execution_instruction"})

print("STEP 3: promotion-time safety — account allowlist (Charter §1) must FAIL-CLOSED")
for bad in ["875691461", "671638849", "000000000"]:
    try:
        safety.assert_account_allowed(bad)
        check(f"reject non-allowlisted {bad}", False)
    except safety.SafetyViolation:
        check(f"reject non-allowlisted {bad}", True)
try:
    safety.assert_account_allowed("696264779")
    check("allow agentic 696264779", True)
except safety.SafetyViolation:
    check("allow agentic 696264779", False)

print("STEP 4: sizing caps (Charter §3) on a $1000 book")
book = 1000.0
# oversize single position (>20% in phase 0) must be rejected
viol_big = safety.check_sizing(book, 0.0, 300.0, "equity")
check("reject oversize single position (>20%)", len(viol_big) > 0)
# a tiny first trade ($150 = 15%) must pass
viol_ok = safety.check_sizing(book, 0.0, 150.0, "equity")
check("accept tiny in-cap position (15%)", len(viol_ok) == 0)

print("STEP 5: build PROPOSED ticket on the happy path (still NOT placed)")
try:
    ticket = safety.build_ticket(
        account_number="696264779", symbol="NVDA", side="buy", type="market",
        book_value=book, deployed_cost=0.0, new_position_cost=150.0,
        asset_class="equity", dollar_amount="150.00",
        rationale=f"e2e dryrun: {pay['thesis']}")
    check("happy-path ticket built", ticket is not None and ticket.account_number == "696264779")
    place_args = ticket.to_place_args()
    check("ticket exposes place args (not auto-placed)", isinstance(place_args, dict))
except Exception as e:
    check("happy-path ticket built", False)
    print("        ERROR:", str(e)[:140])

print("STEP 6: kill-switch (Charter §4) blocks entries when circuit tripped")
ks_tripped = safety.kill_check([{"symbol": "X", "unrealized_pct": -0.30}], 740.0, 1000.0)
check("circuit breaker trips at -26% book DD", ks_tripped["circuit_breaker_tripped"] and not ks_tripped["new_entries_allowed"])
ks_ok = safety.kill_check([], 980.0, 1000.0)
check("entries allowed at small DD", ks_ok["new_entries_allowed"])

# ---- negative: pipeline must refuse to propose a circular/preliminary name --
print("STEP 7: pipeline refuses ineligible (circular / non-authoritative)")
circ = dict(edge); circ["circularity_flag"] = True
cc = conviction_from_verdict(circ, sent)
check("circular EDGE rejected", not cc["eligible"])
prelim = dict(edge); prelim["authoritative"] = False; prelim["verdict"] = "PRELIMINARY_EDGE"
cp = conviction_from_verdict(prelim, sent)
check("preliminary rejected", not cp["eligible"])

# cleanup the dry-run proposal so it can't be mistaken for a real one
(ROOT / path).unlink(missing_ok=True)

n_fail = sum(1 for _, r in results if r == FAIL)
print(f"\n=== {len(results)-n_fail}/{len(results)} checks PASS, {n_fail} FAIL ===")
print("(dry-run proposal artifact removed; nothing placed)")
sys.exit(1 if n_fail else 0)
