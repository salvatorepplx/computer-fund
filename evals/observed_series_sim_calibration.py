"""Offline observed-series calibration readiness for sentiment sim fidelity.

This diagnostic reads only committed sanitized JSONL series fixtures and deterministic
simulator output. It does not call live connectors, broker APIs, live market data,
account/order state, ARMED/EXECUTED flows, or sizing logic.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sim.sentiment_sim import simulate

DEFAULT_SERIES_PATH = REPO_ROOT / "runs" / "sentiment" / "series" / "TICKER_NVDA.jsonl"
MIN_OBSERVED_POINTS_FOR_CALIBRATION = 5
MIN_OBSERVED_SPAN_SECONDS_FOR_LAG = 60 * 60


class ObservedSeriesCalibrationError(AssertionError):
    """Raised when the committed observed series cannot be evaluated offline."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ObservedSeriesCalibrationError(message)


def _repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def _parse_timestamp(value: Any, field: str, line_number: int) -> datetime:
    _require(isinstance(value, str) and value, f"line {line_number} missing non-empty {field}")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - surfaced by CLI/harness
        raise ObservedSeriesCalibrationError(f"line {line_number} has invalid {field}: {value!r}") from exc


def load_observed_series(path: Path = DEFAULT_SERIES_PATH) -> list[dict[str, Any]]:
    """Load and validate a committed sanitized observed sentiment JSONL series."""
    _require(path.exists(), f"observed series fixture missing: {_repo_relative(path)}")
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:  # pragma: no cover - surfaced by CLI/harness
            raise ObservedSeriesCalibrationError(f"line {line_number} must parse as JSON: {exc}") from exc
        _require(isinstance(row, dict), f"line {line_number} must be a JSON object")
        _require(row.get("entity") == "TICKER:NVDA", f"line {line_number} must be the committed NVDA ticker series")
        _require(row.get("source") == "finance_ticker_sentiment", f"line {line_number} must use sanitized finance ticker sentiment")
        _require(isinstance(row.get("score"), int | float), f"line {line_number} score must be numeric")
        _require(-1.0 <= float(row["score"]) <= 1.0, f"line {line_number} score must be normalized to [-1, 1]")
        _require(isinstance(row.get("confidence"), int | float), f"line {line_number} confidence must be numeric")
        _require(0.0 <= float(row["confidence"]) <= 1.0, f"line {line_number} confidence must be normalized to [0, 1]")
        _parse_timestamp(row.get("ts"), "ts", line_number)
        _parse_timestamp(row.get("captured_at"), "captured_at", line_number)
        if "price_proxy" in row:
            _require(isinstance(row["price_proxy"], int | float), f"line {line_number} price_proxy must be numeric when present")
        rows.append(row)

    _require(rows, f"observed series fixture has no observations: {_repo_relative(path)}")
    return sorted(rows, key=lambda item: _parse_timestamp(item["ts"], "ts", 0))


def _round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _deltas(values: list[float]) -> list[float]:
    return [round(values[index] - values[index - 1], 4) for index in range(1, len(values))]


def _sign_changes(deltas: list[float]) -> int:
    nonzero_signs = [math.copysign(1, value) for value in deltas if value != 0]
    return sum(1 for index in range(1, len(nonzero_signs)) if nonzero_signs[index] != nonzero_signs[index - 1])


def summarize_observed_series(rows: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    scores = [float(row["score"]) for row in rows]
    confidences = [float(row["confidence"]) for row in rows]
    timestamps = [_parse_timestamp(row["ts"], "ts", index + 1) for index, row in enumerate(rows)]
    price_values = [float(row["price_proxy"]) for row in rows if isinstance(row.get("price_proxy"), int | float)]
    score_deltas = _deltas(scores)
    price_deltas = _deltas(price_values)
    span_seconds = (timestamps[-1] - timestamps[0]).total_seconds() if len(timestamps) >= 2 else 0.0

    return {
        "path": _repo_relative(path),
        "entity": rows[0]["entity"],
        "source": rows[0]["source"],
        "sample_count": len(rows),
        "first_ts": timestamps[0].isoformat(),
        "last_ts": timestamps[-1].isoformat(),
        "span_seconds": round(span_seconds, 4),
        "score_start": round(scores[0], 4),
        "score_end": round(scores[-1], 4),
        "score_min": round(min(scores), 4),
        "score_max": round(max(scores), 4),
        "score_range": round(max(scores) - min(scores), 4),
        "score_delta_total": round(scores[-1] - scores[0], 4),
        "score_deltas": score_deltas,
        "score_direction_changes": _sign_changes(score_deltas),
        "confidence_mean": round(sum(confidences) / len(confidences), 4),
        "price_proxy_count": len(price_values),
        "price_proxy_start": _round_or_none(price_values[0] if price_values else None),
        "price_proxy_end": _round_or_none(price_values[-1] if price_values else None),
        "price_proxy_delta_total": _round_or_none(price_values[-1] - price_values[0] if len(price_values) >= 2 else None),
        "price_proxy_deltas": price_deltas,
    }


def deterministic_sim_reference(rows: list[dict[str, Any]], *, steps: int, n_agents: int, seed: int) -> dict[str, Any]:
    scores = [float(row["score"]) for row in rows]
    seed_sentiment = scores[0]
    observed_now = scores[-1]
    result = simulate(seed_sentiment=seed_sentiment, observed_now=observed_now, steps=steps, n_agents=n_agents, seed=seed)
    return {
        "params": {
            "seed_sentiment": round(seed_sentiment, 4),
            "observed_now": round(observed_now, 4),
            "steps": steps,
            "n_agents": n_agents,
            "seed": seed,
        },
        "direction": result.direction,
        "edge_score": result.edge_score,
        "peak_step": result.peak_step,
        "peak_value": result.peak_value,
        "current_step_est": result.current_step_est,
        "predate_window": list(result.predate_window),
        "trajectory_start": result.trajectory[0],
        "trajectory_end": result.trajectory[-1],
    }


def calibration_readiness(observed: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    if observed["sample_count"] < MIN_OBSERVED_POINTS_FOR_CALIBRATION:
        blockers.append(
            f"need at least {MIN_OBSERVED_POINTS_FOR_CALIBRATION} observed points; found {observed['sample_count']}"
        )
    if observed["span_seconds"] < MIN_OBSERVED_SPAN_SECONDS_FOR_LAG:
        blockers.append(
            f"need at least {MIN_OBSERVED_SPAN_SECONDS_FOR_LAG} seconds of observed span for lag comparison; "
            f"found {observed['span_seconds']}"
        )
    if observed["price_proxy_count"] < MIN_OBSERVED_POINTS_FOR_CALIBRATION:
        blockers.append(
            f"need at least {MIN_OBSERVED_POINTS_FOR_CALIBRATION} price proxies; found {observed['price_proxy_count']}"
        )

    if blockers:
        return {
            "status": "not_enough_observed_trajectory_data_yet",
            "eligible_for_sim_fidelity_gate": False,
            "blockers": blockers,
        }
    return {
        "status": "ready_for_shape_lag_edge_comparison",
        "eligible_for_sim_fidelity_gate": True,
        "blockers": [],
    }


def run_diagnostic(
    *,
    series_path: Path = DEFAULT_SERIES_PATH,
    steps: int = 30,
    n_agents: int = 400,
    seed: int = 42,
) -> dict[str, Any]:
    rows = load_observed_series(series_path)
    observed = summarize_observed_series(rows, series_path)
    readiness = calibration_readiness(observed)
    sim_reference = deterministic_sim_reference(rows, steps=steps, n_agents=n_agents, seed=seed)
    comparison_status = "skipped_insufficient_observed_data" if not readiness["eligible_for_sim_fidelity_gate"] else "ready"

    return {
        "label": "observed_series_sim_calibration_offline",
        "boundaries": {
            "data_scope": "committed sanitized observed fixtures plus deterministic simulator output only",
            "no_live_connectors": True,
            "no_live_market_data": True,
            "no_broker_or_account_or_order_state": True,
            "no_armed_or_executed_artifacts": True,
            "no_sizing_or_trading_behavior": True,
        },
        "sample_limits": {
            "warning": "Do not claim simulator calibration from the current tiny observed series.",
            "min_observed_points_for_calibration": MIN_OBSERVED_POINTS_FOR_CALIBRATION,
            "min_observed_span_seconds_for_lag": MIN_OBSERVED_SPAN_SECONDS_FOR_LAG,
        },
        "observed_series": observed,
        "sim_reference": sim_reference,
        "comparison": {
            "status": comparison_status,
            "reason": readiness["status"],
            "blockers": readiness["blockers"],
            "note": "Shape, lag, and edge calibration gates must stay closed until readiness is true.",
        },
        "readiness": readiness,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline observed-series sentiment-sim calibration readiness diagnostic.")
    parser.add_argument("--series-path", type=Path, default=DEFAULT_SERIES_PATH)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--n-agents", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(
        json.dumps(
            run_diagnostic(series_path=args.series_path, steps=args.steps, n_agents=args.n_agents, seed=args.seed),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
