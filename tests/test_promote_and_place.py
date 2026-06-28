#!/usr/bin/env python3
"""Standalone gate tests for scripts/promote_and_place.py (Blocker B executor).

Places NOTHING — connector calls are monkeypatched. Complements the gating eval in
evals/run_offline_evals.py (eval_promote_and_place_executor_rails) with deeper coverage of the
fail-closed paths and the happy-path sizing under Phase-0 caps.

Run: env -u PYTHONPATH python tests/test_promote_and_place.py
"""
from __future__ import annotations
import sys, json, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.promote_and_place as P
from execution.safety import SafetyViolation, MAX_SINGLE_POS_FRAC

results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(f"  [{'OK' if cond else 'XX'}] {name}")


def main():
    print("promote_and_place gate tests (places nothing):")

    # --- account allowlist (gate 3) ---
    check("executor bound to allowlisted account", P.ACCOUNT == "696264779")
    P.gate_account_allowlist()  # must not raise
    check("gate_account_allowlist accepts Agentic", True)

    # --- eligibility (gate 1) fail-closed cases ---
    def elig_raises(art):
        try:
            P.gate_eligibility(art); return False
        except P.GateFail:
            return True
    check("eligibility rejects non-EDGE verdict",
          elig_raises({"payload": {"signal_provenance": {"verdict": "PRELIMINARY", "circular": False,
                       "permutation": {"significant_at_0.10": True}}, "entities": ["TICKER:NVDA"]}}))
    check("eligibility rejects circular",
          elig_raises({"payload": {"signal_provenance": {"verdict": "EDGE", "circular": True,
                       "permutation": {"significant_at_0.10": True}}, "entities": ["TICKER:NVDA"]}}))
    check("eligibility rejects missing/insignificant permutation",
          elig_raises({"payload": {"signal_provenance": {"verdict": "EDGE", "circular": False},
                       "entities": ["TICKER:NVDA"]}}))
    elig = P.gate_eligibility({"payload": {"signal_provenance": {"verdict": "EDGE", "circular": False,
                              "permutation": {"significant_at_0.10": True, "p_value": 0.03},
                              "best_lag": 2, "best_corr": 0.65}, "entities": ["TICKER:NVDA"]}})
    check("eligibility accepts fully-eligible artifact", elig["symbol"] == "NVDA")

    # --- price-axis quality (gate 2) ---
    check("price-axis thresholds encode RDDT lesson",
          P.MIN_DISTINCT_PRICES >= 15 and P.MAX_ZERO_RETURN_FRAC <= 0.20 and P.MAX_CAPTURE_GAP_HOURS <= 3.0)

    # --- gate 0 refuses a KILLED artifact ---
    killed = ROOT / "runs" / "KILLED" / "battle-RDDT-leadlag-2026-06-28.json"
    if killed.exists():
        raised = False
        try:
            P.gate_validate_artifact(killed)
        except Exception:
            raised = True
        check("gate 0 refuses KILLED artifact", raised)

    # --- sizing (gate 7) stays within Phase-0 single-position cap ---
    # monkeypatch the connector for review; size via build_ticket path
    P.call_tool = lambda tool, args: {"alerts": []}
    ticket, qty, cost, review = P.gate_size_and_review("NVDA", book_value=1000.0,
                                                       live_price=100.0, rationale="test")
    check("sizing within single-position cap", cost <= MAX_SINGLE_POS_FRAC * 1000.0 + 1e-6)
    check("sizing yields >=1 whole share", qty >= 1)

    # --- blocking broker alert aborts ---
    P.call_tool = lambda tool, args: {"alerts": [{"blocking": True, "reason": "insufficient_buying_power"}]}
    raised = False
    try:
        P.gate_size_and_review("NVDA", 1000.0, 100.0, "test")
    except P.GateFail:
        raised = True
    check("blocking broker alert aborts", raised)

    # --- connector auth error is a blocking gate failure ---
    import subprocess as _sp
    class _R:  # fake a non-zero CLI return
        returncode = 1; stdout = ""; stderr = "auth_required"
    _orig = _sp.run
    _sp.run = lambda *a, **k: _R()
    try:
        raised = False
        try:
            # restore call_tool to the real one so it goes through subprocess
            import importlib
            importlib.reload(P)
            P.gate_account_state()
        except P.GateFail:
            raised = True
        check("connector auth/CLI error fails closed", raised)
    finally:
        _sp.run = _orig
        import importlib; importlib.reload(P)

    passed = sum(1 for _, r in results if r)
    print(f"\n{passed}/{len(results)} checks passed.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
