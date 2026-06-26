"""Deterministic CAP evals and calibration tracking fixtures.

CAP metrics are capability measurements we want to improve over time. This module
only consumes explicit offline rows or future pre-registered observed-history rows;
it does not fetch market data, broker state, account state, or place orders.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MIN_CALIBRATION_SAMPLE_SIZE = 10


@dataclass(frozen=True)
class CapRow:
    thesis_id: str
    projected_peak_step: int
    observed_peak_step: int
    projected_peak_sentiment: float
    observed_peak_sentiment: float
    entry_step: int | None
    expected_edge: float
    realized_return: float
    benchmark_return: float
    round_trip_cost: float
    conviction: float | None = None
    closed: bool = True

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "CapRow":
        return cls(
            thesis_id=str(row["thesis_id"]),
            projected_peak_step=int(row["projected_peak_step"]),
            observed_peak_step=int(row["observed_peak_step"]),
            projected_peak_sentiment=float(row["projected_peak_sentiment"]),
            observed_peak_sentiment=float(row["observed_peak_sentiment"]),
            entry_step=None if row.get("entry_step") is None else int(row["entry_step"]),
            expected_edge=float(row["expected_edge"]),
            realized_return=float(row["realized_return"]),
            benchmark_return=float(row["benchmark_return"]),
            round_trip_cost=float(row["round_trip_cost"]),
            conviction=None if row.get("conviction") is None else float(row["conviction"]),
            closed=bool(row.get("closed", True)),
        )


FIXTURE_ROWS = (
    CapRow("fixture_bull_early", 5, 6, 0.46, 0.43, 2, 0.060, 0.050, 0.020, 0.006, 0.82),
    CapRow("fixture_bear_early", 4, 3, -0.38, -0.42, 1, 0.050, 0.015, 0.030, 0.004, 0.70),
    CapRow("fixture_late_peak", 7, 9, 0.31, 0.25, 8, 0.030, 0.010, 0.005, 0.003, 0.55),
    CapRow("fixture_no_entry", 6, 5, -0.28, -0.21, None, 0.020, 0.000, 0.010, 0.000, 0.35, closed=False),
)


def sentiment_peak_error(row: CapRow) -> float:
    return abs(row.projected_peak_sentiment - row.observed_peak_sentiment)


def predate_timing_steps(row: CapRow) -> int | None:
    if row.entry_step is None:
        return None
    return row.observed_peak_step - row.entry_step


def edge_after_costs(row: CapRow) -> float:
    return row.realized_return - row.benchmark_return - row.round_trip_cost


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(statistics.fmean(values), 6)


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return None
    return round(numerator / (denom_x * denom_y), 6)


def summarize_rows(rows: list[CapRow]) -> dict[str, Any]:
    if not rows:
        raise ValueError("at least one CAP row is required")

    timing_values = [predate_timing_steps(row) for row in rows]
    observed_timing_values = [float(value) for value in timing_values if value is not None]
    closed_rows = [row for row in rows if row.closed and row.conviction is not None]
    calibration_ready = len(closed_rows) >= MIN_CALIBRATION_SAMPLE_SIZE

    return {
        "label": "cap_calibration_offline_fixture",
        "note": "Deterministic fixture/pre-registration metrics only; no live data or trading advice.",
        "minimum_calibration_sample_size": MIN_CALIBRATION_SAMPLE_SIZE,
        "row_count": len(rows),
        "sentiment_peak_error_mean": _mean([sentiment_peak_error(row) for row in rows]),
        "predate_timing_steps_mean": _mean(observed_timing_values),
        "predate_success_rate": _mean([1.0 if value is not None and value > 0 else 0.0 for value in timing_values]),
        "edge_after_costs_mean": _mean([edge_after_costs(row) for row in rows]),
        "edge_after_costs_positive_rate": _mean([1.0 if edge_after_costs(row) > 0 else 0.0 for row in rows]),
        "calibration": {
            "closed_with_conviction_count": len(closed_rows),
            "ready": calibration_ready,
            "conviction_edge_after_costs_pearson": _pearson(
                [row.conviction for row in closed_rows if row.conviction is not None],
                [edge_after_costs(row) for row in closed_rows],
            ) if calibration_ready else None,
        },
        "rows": [
            {
                "thesis_id": row.thesis_id,
                "sentiment_peak_error": round(sentiment_peak_error(row), 6),
                "predate_timing_steps": predate_timing_steps(row),
                "edge_after_costs": round(edge_after_costs(row), 6),
                "closed": row.closed,
            }
            for row in rows
        ],
    }


def load_rows(path: Path) -> list[CapRow]:
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError("CAP rows file must be a JSON array")
    return [CapRow.from_mapping(row) for row in data]


def run_metrics(rows: list[CapRow] | None = None) -> dict[str, Any]:
    return summarize_rows(list(rows or FIXTURE_ROWS))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline CAP calibration fixture metrics.")
    parser.add_argument("--rows-json", type=Path, help="Optional JSON array of pre-registered CAP rows.")
    args = parser.parse_args()
    rows = load_rows(args.rows_json) if args.rows_json else list(FIXTURE_ROWS)
    print(json.dumps(run_metrics(rows), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
