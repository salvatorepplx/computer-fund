"""Deterministic sentiment lead-lag placebo checks for offline evals.

The fixture data in this module is fully simulated. It tests the shape of the
falsifier Computer Fund needs before trusting sentiment-alpha hypotheses: a
projected sentiment signal must lead a later observed sentiment/price proxy, and
coincident, lagging, random-label, and wrong-universe controls must be rejected.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LeadLagFixture:
    name: str
    predicted_sentiment: tuple[float, ...]
    observed_proxy: tuple[float, ...]
    expected_accept: bool
    reason: str


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0

    left_mean = _mean(left)
    right_mean = _mean(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    numerator = sum(a * b for a, b in zip(left_centered, right_centered, strict=True))
    left_var = sum(value * value for value in left_centered)
    right_var = sum(value * value for value in right_centered)
    denominator = math.sqrt(left_var * right_var)
    return numerator / denominator if denominator else 0.0


def _aligned_series(predicted: tuple[float, ...], observed: tuple[float, ...], lag: int) -> tuple[list[float], list[float]]:
    if lag >= 0:
        end = min(len(predicted), len(observed) - lag)
        return list(predicted[:end]), list(observed[lag:lag + end])

    offset = -lag
    end = min(len(predicted) - offset, len(observed))
    return list(predicted[offset:offset + end]), list(observed[:end])


def _directional_peak_step(values: tuple[float, ...], direction: int) -> int:
    return max(range(len(values)), key=lambda index: direction * values[index])


def evaluate_fixture(
    fixture: LeadLagFixture,
    *,
    min_lead_steps: int = 2,
    max_lag_steps: int = 5,
    min_correlation: float = 0.72,
) -> dict[str, Any]:
    if len(fixture.predicted_sentiment) != len(fixture.observed_proxy):
        raise ValueError(f"{fixture.name}: predicted and observed series must be the same length")
    if min_lead_steps < 1:
        raise ValueError("min_lead_steps must be positive")

    direction = 1 if max(fixture.predicted_sentiment) >= abs(min(fixture.predicted_sentiment)) else -1
    predicted_peak_step = _directional_peak_step(fixture.predicted_sentiment, direction)
    observed_peak_step = _directional_peak_step(fixture.observed_proxy, direction)
    peak_lead_steps = observed_peak_step - predicted_peak_step

    lag_correlations = []
    for lag in range(-max_lag_steps, max_lag_steps + 1):
        predicted_slice, observed_slice = _aligned_series(fixture.predicted_sentiment, fixture.observed_proxy, lag)
        lag_correlations.append({"lag": lag, "correlation": round(_pearson(predicted_slice, observed_slice), 4)})

    best = max(lag_correlations, key=lambda row: (row["correlation"], row["lag"]))
    accepted = (
        peak_lead_steps >= min_lead_steps
        and best["lag"] >= min_lead_steps
        and best["correlation"] >= min_correlation
    )

    return {
        "name": fixture.name,
        "label": "simulated_fixture_not_market_data",
        "reason": fixture.reason,
        "expected_accept": fixture.expected_accept,
        "accepted": accepted,
        "matches_expectation": accepted == fixture.expected_accept,
        "direction": "bull" if direction > 0 else "bear",
        "predicted_peak_step": predicted_peak_step,
        "observed_peak_step": observed_peak_step,
        "peak_lead_steps": peak_lead_steps,
        "best_lag_steps": best["lag"],
        "best_correlation": best["correlation"],
        "thresholds": {
            "min_lead_steps": min_lead_steps,
            "min_correlation": min_correlation,
            "max_lag_steps": max_lag_steps,
        },
    }


FIXTURES = (
    LeadLagFixture(
        name="bullish_sentiment_leads_proxy",
        predicted_sentiment=(0.0, 0.2, 0.6, 1.0, 0.7, 0.3, 0.1, 0.0, 0.0, 0.0),
        observed_proxy=(0.0, 0.0, 0.0, 0.0, 0.2, 0.6, 1.0, 0.7, 0.3, 0.1),
        expected_accept=True,
        reason="Positive control: projected sentiment peak precedes the observed proxy peak by three steps.",
    ),
    LeadLagFixture(
        name="coincident_sentiment_proxy",
        predicted_sentiment=(0.0, 0.1, 0.4, 0.9, 1.0, 0.6, 0.2, 0.0, 0.0, 0.0),
        observed_proxy=(0.0, 0.1, 0.4, 0.9, 1.0, 0.6, 0.2, 0.0, 0.0, 0.0),
        expected_accept=False,
        reason="Coincident placebo: the proxy moves at the same time, so there is no predate edge.",
    ),
    LeadLagFixture(
        name="lagging_sentiment_follows_proxy",
        predicted_sentiment=(0.0, 0.0, 0.0, 0.1, 0.3, 0.7, 1.0, 0.6, 0.2, 0.0),
        observed_proxy=(0.0, 0.2, 0.6, 1.0, 0.7, 0.3, 0.1, 0.0, 0.0, 0.0),
        expected_accept=False,
        reason="Lagging placebo: projected sentiment follows the proxy instead of leading it.",
    ),
    LeadLagFixture(
        name="random_label_placebo",
        predicted_sentiment=(0.0, 0.7, -0.4, 0.5, -0.6, 0.2, 0.1, -0.3, 0.4, -0.2),
        observed_proxy=(0.0, 0.0, 0.1, 0.3, 0.6, 1.0, 0.7, 0.3, 0.1, 0.0),
        expected_accept=False,
        reason="Random-label placebo: shuffled sentiment labels should not survive the lead-lag gate.",
    ),
    LeadLagFixture(
        name="wrong_universe_placebo",
        predicted_sentiment=(0.0, 0.2, 0.6, 1.0, 0.7, 0.3, 0.1, 0.0, 0.0, 0.0),
        observed_proxy=(0.0, -0.1, -0.3, -0.6, -0.9, -0.6, -0.3, -0.1, 0.0, 0.0),
        expected_accept=False,
        reason="Universe placebo: the signal is tested against an unrelated inverse proxy.",
    ),
)


def run_leadlag_placebo_checks() -> dict[str, Any]:
    fixture_results = [evaluate_fixture(fixture) for fixture in FIXTURES]
    return {
        "label": "sentiment_leadlag_placebo_offline_fixture",
        "note": "Deterministic simulated fixtures only; no broker connectors, live market data, account state, orders, or recommendations.",
        "all_expectations_met": all(result["matches_expectation"] for result in fixture_results),
        "fixtures": fixture_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic offline sentiment lead-lag placebo checks.")
    parser.parse_args()
    result = run_leadlag_placebo_checks()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["all_expectations_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
