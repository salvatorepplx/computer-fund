"""Offline per-source sentiment trust learning fixture.

This module is deliberately connector-free. It consumes deterministic simulated
lead-lag fixtures plus simulated CAP source attribution rows to show how future
sanitized observed artifacts can update source priors without touching broker
connectors, live market data, account state, orders, or sizing.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from typing import Any

from evals.leadlag_placebo import FIXTURES, LeadLagFixture, evaluate_fixture


OBSERVED_EVENT_THRESHOLD = 10


@dataclass(frozen=True)
class SourceAttributionFixture:
    source_id: str
    source_type: str
    fixture: LeadLagFixture
    observed_event_count: int
    prior_weight: float
    cap_source_attribution: float


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None

    left_mean = _mean(left)
    right_mean = _mean(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    numerator = sum(a * b for a, b in zip(left_centered, right_centered, strict=True))
    left_var = sum(value * value for value in left_centered)
    right_var = sum(value * value for value in right_centered)
    denominator = math.sqrt(left_var * right_var)
    return numerator / denominator if denominator else None


def _fixture_by_name(name: str) -> LeadLagFixture:
    return next(fixture for fixture in FIXTURES if fixture.name == name)


SOURCE_ATTRIBUTION_FIXTURES = (
    SourceAttributionFixture(
        source_id="fixture.leading_social",
        source_type="simulated_fixture",
        fixture=_fixture_by_name("bullish_sentiment_leads_proxy"),
        observed_event_count=12,
        prior_weight=0.5,
        cap_source_attribution=0.018,
    ),
    SourceAttributionFixture(
        source_id="fixture.lagging_correlated_aggregate",
        source_type="simulated_fixture_deliberately_lagging",
        fixture=_fixture_by_name("lagging_sentiment_follows_proxy"),
        observed_event_count=12,
        prior_weight=0.5,
        cap_source_attribution=-0.004,
    ),
    SourceAttributionFixture(
        source_id="fixture.coincident_news",
        source_type="simulated_fixture",
        fixture=_fixture_by_name("coincident_sentiment_proxy"),
        observed_event_count=12,
        prior_weight=0.5,
        cap_source_attribution=0.002,
    ),
    SourceAttributionFixture(
        source_id="fixture.random_label_control",
        source_type="simulated_fixture_placebo",
        fixture=_fixture_by_name("random_label_placebo"),
        observed_event_count=12,
        prior_weight=0.5,
        cap_source_attribution=-0.012,
    ),
)


def score_source_attribution(source: SourceAttributionFixture) -> dict[str, Any]:
    leadlag = evaluate_fixture(source.fixture)
    enough_events = source.observed_event_count >= OBSERVED_EVENT_THRESHOLD
    measured_lead_steps = leadlag["peak_lead_steps"]
    median_lag_steps = max(0, -leadlag["best_lag_steps"])
    correlation = max(0.0, leadlag["best_correlation"])
    measured_lead_score = measured_lead_steps * correlation if leadlag["accepted"] or measured_lead_steps < 0 else 0.0

    lead_component = _clamp((measured_lead_score + 5) / 10)
    cap_component = _clamp((source.cap_source_attribution + 0.02) / 0.04)
    evidence_weight = (0.75 * lead_component) + (0.25 * cap_component)
    learned_prior_weight = source.prior_weight if not enough_events else (0.25 * source.prior_weight) + (0.75 * evidence_weight)

    return {
        "source_id": source.source_id,
        "source_type": source.source_type,
        "label": "simulated_fixture_not_market_data",
        "event_count": source.observed_event_count,
        "observed_event_threshold": OBSERVED_EVENT_THRESHOLD,
        "enough_events_to_update": enough_events,
        "prior_weight": round(source.prior_weight, 6),
        "measured_lead_steps": measured_lead_steps,
        "measured_lead_score": round(measured_lead_score, 6),
        "median_lag_steps": median_lag_steps,
        "best_lag_steps": leadlag["best_lag_steps"],
        "best_correlation": leadlag["best_correlation"],
        "leadlag_accepted": leadlag["accepted"],
        "cap_source_attribution": round(source.cap_source_attribution, 6),
        "lead_component": round(lead_component, 6),
        "cap_component": round(cap_component, 6),
        "learned_prior_weight": round(learned_prior_weight, 6),
    }


def run_source_weight_learning_fixture(
    sources: tuple[SourceAttributionFixture, ...] = SOURCE_ATTRIBUTION_FIXTURES,
) -> dict[str, Any]:
    source_metrics = [score_source_attribution(source) for source in sources]
    total_weight = sum(row["learned_prior_weight"] for row in source_metrics)
    for row in source_metrics:
        row["normalized_effective_weight"] = round(row["learned_prior_weight"] / total_weight, 6)

    leading = next(row for row in source_metrics if row["source_id"] == "fixture.leading_social")
    lagging = next(row for row in source_metrics if row["source_id"] == "fixture.lagging_correlated_aggregate")
    weight_lead_correlation = _pearson(
        [row["measured_lead_score"] for row in source_metrics],
        [row["learned_prior_weight"] for row in source_metrics],
    )

    return {
        "label": "sentiment_source_weight_learning_offline_fixture",
        "note": "Deterministic simulated fixtures only; no broker connectors, live market data, account state, orders, or recommendations.",
        "source_metrics": source_metrics,
        "success_criteria": {
            "minimum_observed_events": OBSERVED_EVENT_THRESHOLD,
            "all_sources_have_enough_events": all(row["enough_events_to_update"] for row in source_metrics),
            "learned_weights_correlate_with_measured_lead": round(weight_lead_correlation, 6)
            if weight_lead_correlation is not None
            else None,
            "leading_source_weight_gt_lagging_source_weight": (
                leading["learned_prior_weight"] > lagging["learned_prior_weight"]
            ),
            "lagging_source_demoted_below_prior": lagging["learned_prior_weight"] < lagging["prior_weight"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline per-source sentiment weight learning fixture.")
    parser.parse_args()
    result = run_source_weight_learning_fixture()
    print(json.dumps(result, indent=2, sort_keys=True))
    criteria = result["success_criteria"]
    return 0 if all(
        (
            criteria["all_sources_have_enough_events"],
            criteria["learned_weights_correlate_with_measured_lead"] > 0.5,
            criteria["leading_source_weight_gt_lagging_source_weight"],
            criteria["lagging_source_demoted_below_prior"],
        )
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
