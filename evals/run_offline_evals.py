"""Offline eval harness for the Computer Fund.

These evals are deterministic and connector-free. They encode Charter safety rails,
observed-vs-simulated sentiment boundaries, deterministic battle ranking, and basic
simulation invariants without touching broker connectors, live market data, account
state, or order placement.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.cap_calibration import MIN_CALIBRATION_SAMPLE_SIZE, run_metrics as run_cap_metrics
from execution.safety import (
    MAX_OPTION_PREMIUM_FRAC,
    MAX_SINGLE_POS_FRAC,
    MAX_TOTAL_DEPLOYED_FRAC,
    SafetyViolation,
    build_ticket,
    check_sizing,
    kill_check,
)
from graph.kg import KnowledgeGraph
from evals.kg_observed_series import MIN_SERIES_ROWS_FOR_READINESS, run_kg_observed_series_diagnostic
from evals.leadlag_placebo import run_leadlag_placebo_checks
from evals.observed_sentiment_fixture import validate_observed_finance_fixture
from evals.source_weight_learning import OBSERVED_EVENT_THRESHOLD, run_source_weight_learning_fixture
from research.battle_discovery import discover_battles, score_battle
from sim.sentiment_sim import predate_signal, simulate


class EvalFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvalFailure(message)


def require_raises(expected_exception: type[BaseException], fn, message: str) -> None:
    try:
        fn()
    except expected_exception:
        return
    except Exception as exc:  # pragma: no cover - surfaced by runner output
        raise EvalFailure(f"{message}: raised {type(exc).__name__}, expected {expected_exception.__name__}") from exc
    raise EvalFailure(f"{message}: did not raise {expected_exception.__name__}")


def eval_safety_rails_fail_closed() -> None:
    book_value = 1000
    single_cap_amount = MAX_SINGLE_POS_FRAC * book_value
    total_deployed_cap_amount = MAX_TOTAL_DEPLOYED_FRAC * book_value
    option_cap_amount = MAX_OPTION_PREMIUM_FRAC * book_value

    for account in ("671638849", "875691461", "999999999", ""):
        require_raises(
            SafetyViolation,
            lambda account=account: build_ticket(
                account_number=account,
                symbol="NVDA",
                side="buy",
                type="market",
                book_value=book_value,
                deployed_cost=0,
                new_position_cost=100,
                dollar_amount="100",
                rationale="offline eval only",
            ),
            f"account {account!r} must fail closed",
        )

    require(
        check_sizing(book_value, 0, single_cap_amount, "equity") == [],
        "single-position cap should allow exactly the active phase cap",
    )
    require(
        check_sizing(book_value, 0, single_cap_amount + 0.01, "equity"),
        "single-position cap should reject more than the active phase cap",
    )
    require_raises(
        SafetyViolation,
        lambda: build_ticket(
            account_number="696264779",
            symbol="NVDA",
            side="buy",
            type="market",
            book_value=book_value,
            deployed_cost=0,
            new_position_cost=single_cap_amount + 0.01,
            dollar_amount=f"{single_cap_amount + 0.01:.2f}",
            rationale="offline eval only",
        ),
        "build_ticket should enforce the single-position cap for buys",
    )
    require(
        check_sizing(book_value, total_deployed_cap_amount - 100, 100.01, "equity"),
        "total deployed cap should reject more than the active phase cap",
    )
    require(
        check_sizing(book_value, 0, 50, "option", option_premium_at_risk=option_cap_amount + 0.01),
        "option premium cap should reject more than the active phase cap",
    )
    require_raises(
        SafetyViolation,
        lambda: build_ticket(
            account_number="696264779",
            symbol="NVDA",
            side="buy",
            type="limit",
            book_value=book_value,
            deployed_cost=0,
            new_position_cost=50,
            asset_class="option",
            quantity="1",
            limit_price="0.50",
            rationale="offline eval only",
            option_premium_at_risk=option_cap_amount + 0.01,
        ),
        "build_ticket should enforce the option-premium cap for buys",
    )

    ticket = build_ticket(
        account_number="696264779",
        symbol="NVDA",
        side="buy",
        type="market",
        book_value=book_value,
        deployed_cost=0,
        new_position_cost=100,
        dollar_amount="100",
        rationale="offline eval only",
    )
    require(ticket.status == "PROPOSED", "allowed ticket should remain only PROPOSED")
    require(ticket.to_place_args()["account_number"] == "696264779", "place args should target Agentic only")

    kill = kill_check(
        positions=[{"symbol": "NVDA", "unrealized_pct": -0.25}, {"symbol": "AAPL", "unrealized_pct": -0.05}],
        book_value=850,
        hwm=1000,
    )
    require(kill["position_stops"] == ["NVDA"], "-25% position stop should be flagged")
    require(kill["circuit_breaker_tripped"], "-15% book drawdown should trip circuit breaker")
    require(not kill["new_entries_allowed"], "circuit breaker should block new entries")


def eval_knowledge_graph_observed_sentiment() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "knowledge_graph.json"
        kg = KnowledgeGraph(path)
        kg.upsert_node("BATTLE:TEST", "battle", label="offline eval battle")
        kg.add_sentiment("BATTLE:TEST", 0.1, 0.7, "eval:observed-1", simulated=False)
        kg.add_sentiment("BATTLE:TEST", 0.3, 0.8, "eval:observed-2", simulated=False)
        kg.add_sentiment("BATTLE:TEST", 0.9, 0.4, "eval:simulated", simulated=True)

        latest_observed = kg.latest_sentiment("BATTLE:TEST")
        latest_any = kg.latest_sentiment("BATTLE:TEST", observed_only=False)
        require(latest_observed is not None, "latest observed sentiment should exist")
        require(latest_observed["score"] == 0.3, "latest_sentiment defaults to observed-only")
        require(latest_observed["simulated"] is False, "observed-only latest must not return simulated data")
        require(latest_any is not None and latest_any["score"] == 0.9, "latest any should return final item")
        require(latest_any["simulated"] is True, "explicit full latest may return simulated data")
        require(kg.sentiment_momentum("BATTLE:TEST") == 0.2, "momentum should ignore simulated sentiment by default")
        require(kg.sentiment_momentum("BATTLE:TEST", observed_only=False) == 0.6, "explicit full momentum may include simulated data")

        saved_path = kg.save()
        reloaded = KnowledgeGraph(saved_path)
        require(reloaded.latest_sentiment("BATTLE:TEST")["score"] == 0.3, "saved graph should reload latest observed sentiment")
        require(reloaded.summary()["ticks"] == 1, "save should bump tick count once")


def eval_battle_discovery_deterministic_ranking() -> None:
    movers = [
        {"symbol": "NVDA", "pct_change": -4.2, "volume": 500_000_000},
        {"symbol": "RDDT", "pct_change": 9.1, "volume": 30_000_000},
        {"symbol": "SMCI", "pct_change": 12.5, "volume": 40_000_000},
    ]
    earnings = [{"symbol": "NVDA", "report_date": "2026-08-27", "when": "pm"}]
    sentiment = {
        "NVDA": {"score": -0.3, "confidence": 0.4},
        "RDDT": {"score": 0.6, "confidence": 0.55},
        "SMCI": {"score": 0.1, "confidence": 0.2},
        "AAPL": {"score": 0.0, "confidence": 0.5},
    }

    expected = discover_battles(movers, earnings, sentiment, top_k=4)
    require(discover_battles(list(reversed(movers)), earnings, sentiment, top_k=4) == expected,
            "battle discovery ranking should be deterministic across input order")

    require([battle["symbol"] for battle in expected] == ["NVDA", "RDDT", "SMCI", "AAPL"],
            "battle ranking should follow score then stable symbol tie-break")
    require(expected[0]["seed_direction"] == -1.0, "negative sentiment plus move should seed bearish direction")

    score = score_battle("TIE", {"pct_change": 0.0}, False, {"score": 0.0, "confidence": 0.5})
    require(score["score"] == 0.075, "score components should stay stable for neutral input")


def eval_sentiment_sim_deterministic_invariants() -> None:
    bull = simulate(seed_sentiment=0.5, observed_now=0.02, n_agents=120, steps=16, seed=42)
    bull_repeat = simulate(seed_sentiment=0.5, observed_now=0.02, n_agents=120, steps=16, seed=42)
    bear = simulate(seed_sentiment=-0.5, observed_now=-0.02, n_agents=120, steps=16, seed=42)

    require(bull.to_dict() == bull_repeat.to_dict(), "simulation should be deterministic for fixed seed")
    require(len(bull.trajectory) == 16, "trajectory length should match requested steps")
    require(all(-1.0 <= value <= 1.0 for value in bull.trajectory), "sentiment trajectory should remain bounded")
    require(bull.direction == "bull", "positive seed should produce bull direction")
    require(bear.direction == "bear", "negative seed should produce bear direction")
    require(0 <= bull.predate_window[0] <= bull.predate_window[1] <= bull.peak_step < 16,
            "predate window should precede projected peak")

    signal = predate_signal(bull)
    require(set(signal) == {"act", "direction", "edge_score", "steps_to_projected_peak", "reason"},
            "predate signal should expose stable keys")
    require(signal["direction"] == bull.direction, "predate signal direction should match sim direction")
    require(signal["edge_score"] == bull.edge_score, "predate signal edge should match sim edge")
    require(signal["steps_to_projected_peak"] == bull.peak_step - bull.current_step_est,
            "steps to peak should be derived from observed-current estimate")
    require("projected" in signal["reason"], "signal reason should label simulated projection as projected")


def eval_sentiment_leadlag_placebo() -> None:
    result = run_leadlag_placebo_checks()
    require(result["all_expectations_met"], "lead-lag placebo fixtures should accept only the true leading signal")


def eval_cap_calibration_fixture_metrics() -> None:
    metrics = run_cap_metrics()

    require(metrics["label"] == "cap_calibration_offline_fixture", "CAP metrics should use fixture label")
    require(metrics["row_count"] == 4, "CAP fixture row count should remain deterministic")
    require(metrics["minimum_calibration_sample_size"] == MIN_CALIBRATION_SAMPLE_SIZE,
            "CAP tracker should report the pre-registered calibration sample size")
    require(metrics["sentiment_peak_error_mean"] == 0.05, "CAP sentiment peak error fixture mean should be stable")
    require(metrics["predate_timing_steps_mean"] == 2.333333, "CAP predate timing fixture mean should be stable")
    require(metrics["predate_success_rate"] == 0.75, "CAP predate success fixture rate should be stable")
    require(metrics["edge_after_costs_mean"] == -0.00075, "CAP edge-after-costs fixture mean should be stable")
    require(metrics["edge_after_costs_positive_rate"] == 0.5,
            "CAP edge-after-costs positive fixture rate should be stable")
    require(metrics["calibration"]["closed_with_conviction_count"] == 3,
            "CAP calibration should only count closed rows with conviction")
    require(metrics["calibration"]["ready"] is False, "CAP calibration should wait for the minimum sample size")
    require(metrics["calibration"]["conviction_edge_after_costs_pearson"] is None,
            "CAP conviction correlation should stay withheld before enough closed rows")


def eval_sentiment_source_weight_learning() -> None:
    result = run_source_weight_learning_fixture()
    source_metrics = {row["source_id"]: row for row in result["source_metrics"]}
    criteria = result["success_criteria"]
    leading = source_metrics["fixture.leading_social"]
    lagging = source_metrics["fixture.lagging_correlated_aggregate"]

    require(result["label"] == "sentiment_source_weight_learning_offline_fixture",
            "source weight learning should use the offline fixture label")
    require(criteria["minimum_observed_events"] == OBSERVED_EVENT_THRESHOLD,
            "source weight learning should report the event threshold")
    require(criteria["all_sources_have_enough_events"],
            "source weight fixture should update only after enough observed events")
    require(criteria["learned_weights_correlate_with_measured_lead"] > 0.5,
            "learned source weights should correlate with measured lead")
    require(criteria["leading_source_weight_gt_lagging_source_weight"],
            "leading fixture source should earn more trust than lagging source")
    require(criteria["lagging_source_demoted_below_prior"],
            "lagging correlated source should be demoted below its prior")
    require(leading["measured_lead_steps"] > 0 and leading["leadlag_accepted"],
            "leading source should pass lead-lag attribution")
    require(lagging["best_correlation"] > 0.9 and lagging["measured_lead_steps"] < 0,
            "lagging fixture should stay correlated while following the proxy")
    require(lagging["learned_prior_weight"] < leading["learned_prior_weight"],
            "lagging source learned trust should be lower than leading source trust")


def eval_observed_finance_sentiment_fixture() -> None:
    result = validate_observed_finance_fixture()
    event = result["event"]
    raw_reference = result["raw_reference"]
    compatibility = result["source_weight_compatibility"]

    require(result["label"] == "observed_finance_ticker_sentiment_fixture_validation",
            "observed fixture eval should use the stable validation label")
    require(result["mode"] == "offline_propose_only_no_fetch",
            "observed fixture eval must stay offline/propose-only")
    require(result["observed_labeling"]["doc_labels_observed"],
            "fixture must be explicitly labeled OBSERVED")
    require(result["observed_labeling"]["doc_labels_not_simulated"],
            "fixture must be explicitly labeled NOT simulated")
    require(event["source"] == "finance_ticker_sentiment", "event source should identify the adapter output")
    require(event["venue"] == "vendor.finance", "event venue should support source/venue attribution")
    require(event["missing_time_fields"] == [],
            "timestamped observed fixture should report available timestamp fields")
    require(raw_reference["raw_ref_present_in_event"],
            "timestamped observed fixture should carry normalized_event.raw_ref provenance")
    require(raw_reference["raw_reference_chars"] == event["raw_counts"]["chars"],
            "raw reference should match sanitized character count")
    require(compatibility["source_key"] == "finance_ticker_sentiment::vendor.finance",
            "observed fixture should expose source/venue grouping for weighting plumbing")
    require(compatibility["leadlag_credit_allowed"] is False,
            "single observed fixture must not earn lead-lag/CAP credit")


def eval_kg_observed_series_diagnostic() -> None:
    result = run_kg_observed_series_diagnostic()
    latest = result["latest_observed"]
    readiness = result["readiness"]

    require(result["label"] == "kg_observed_series_offline_diagnostic",
            "KG series diagnostic should use the stable validation label")
    require(result["mode"] == "offline_propose_only_no_fetch_no_trading",
            "KG series diagnostic must stay offline/propose-only")
    require(result["series_path"] == "runs/sentiment/series/TICKER_NVDA.jsonl",
            "KG series diagnostic should read the committed NVDA observed series")
    require(result["entity"] == "TICKER:NVDA", "KG series diagnostic should replay NVDA ticker sentiment")
    require(result["source"] == "finance_ticker_sentiment", "KG series diagnostic should preserve source")
    require(result["row_count"] == 3, "committed NVDA observed series row count should stay deterministic")
    require(set(result["required_fields"]) == {"captured_at", "entity", "score", "confidence", "source", "ts", "event_id"},
            "KG series diagnostic should validate timestamp/provenance fields available in the series")
    require(result["observed_rows_simulated_flags"] == [False, False, False],
            "KG replayed observed rows must remain simulated:false")
    require(latest["score"] == 0.5 and latest["simulated"] is False,
            "KG latest observed should return the final non-simulated row")
    require(latest["event_id"] == "sha256:88c1a4c35775620d",
            "KG latest observed should preserve event_id provenance")
    require(result["momentum"] == result["expected_momentum"] == 0.8333,
            "KG momentum should use observed-only history from the committed series")
    require(readiness["minimum_observed_rows"] == MIN_SERIES_ROWS_FOR_READINESS,
            "KG series diagnostic should report the readiness threshold")
    require(readiness["ready_for_leadlag_or_current_step_credit"] is False,
            "short observed series must not claim lead-lag/current-step readiness")


EVALS = [
    eval_safety_rails_fail_closed,
    eval_knowledge_graph_observed_sentiment,
    eval_battle_discovery_deterministic_ranking,
    eval_sentiment_sim_deterministic_invariants,
    eval_sentiment_leadlag_placebo,
    eval_cap_calibration_fixture_metrics,
    eval_sentiment_source_weight_learning,
    eval_observed_finance_sentiment_fixture,
    eval_kg_observed_series_diagnostic,
]


def main() -> int:
    results = []
    failures = []
    for eval_fn in EVALS:
        try:
            eval_fn()
        except Exception as exc:
            results.append({"name": eval_fn.__name__, "status": "FAIL", "error": str(exc)})
            failures.append(exc)
        else:
            results.append({"name": eval_fn.__name__, "status": "PASS"})

    print(json.dumps({"offline_evals": results}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
