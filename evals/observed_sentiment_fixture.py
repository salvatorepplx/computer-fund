"""Offline validation for sanitized observed sentiment fixtures.

This module is deliberately connector-free. It validates Computer-committed,
sanitized fixture artifacts against the RFC-001 SentimentEvent contract subset
available in the artifact without calling live adapters, broker APIs, market data,
account state, orders, sizing, or ARMED handoffs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE_PATH = REPO_ROOT / "runs" / "sentiment" / "fixtures" / "finance_ticker_sentiment_NVDA.json"
EXPECTED_SOURCE = "finance_ticker_sentiment"
EXPECTED_VENUE = "vendor.finance"
EXPECTED_ENTITY = "TICKER:NVDA"
REQUIRED_TIME_FIELDS = ("ts", "observed_at", "ingested_at")


class ObservedFixtureValidationError(AssertionError):
    """Raised when a sanitized observed fixture violates the offline contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ObservedFixtureValidationError(message)


def _repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def _load_fixture(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced by CLI/harness
        raise ObservedFixtureValidationError(f"fixture must parse as JSON: {exc}") from exc
    _require(isinstance(data, dict), "fixture top-level must be a JSON object")
    return data


def _label_text(fixture: dict[str, Any]) -> str:
    return " ".join(str(fixture.get(key, "")) for key in ("_doc", "note"))


def _validate_observed_labeling(fixture: dict[str, Any]) -> dict[str, Any]:
    text = _label_text(fixture).upper()
    event = fixture.get("normalized_event", {})
    labels = event.get("labels", {}) if isinstance(event, dict) else {}
    simulated_label = labels.get("simulated") if isinstance(labels, dict) else None

    _require("OBSERVED" in text, "fixture docs must explicitly label the artifact OBSERVED")
    _require("NOT SIMULATED" in text or "NON-SIMULATED" in text,
             "fixture docs must explicitly say the artifact is not simulated")
    _require(simulated_label is not True, "observed fixture must not set labels.simulated=true")

    return {
        "doc_labels_observed": "OBSERVED" in text,
        "doc_labels_not_simulated": "NOT SIMULATED" in text or "NON-SIMULATED" in text,
        "labels_simulated": simulated_label,
    }


def _validate_event_shape(fixture: dict[str, Any]) -> dict[str, Any]:
    event = fixture.get("normalized_event")
    _require(isinstance(event, dict), "fixture must contain normalized_event object")
    _require(fixture.get("source") == EXPECTED_SOURCE, "fixture source must match finance ticker sentiment source")
    _require(fixture.get("entity") == EXPECTED_ENTITY, "fixture entity must match NVDA ticker entity")

    for field in ("entity", "entity_type", "score", "confidence", "source", "venue", "raw"):
        _require(field in event, f"normalized_event missing required field available in first fixture: {field}")

    _require(event["entity"] == EXPECTED_ENTITY, "normalized_event entity must match top-level entity")
    _require(event["entity_type"] == "ticker", "normalized_event entity_type must be ticker")
    _require(event["source"] == EXPECTED_SOURCE, "normalized_event source must match finance ticker sentiment")
    _require(event["venue"] == EXPECTED_VENUE, "normalized_event venue must match vendor.finance")
    _require(isinstance(event["score"], int | float), "score must be numeric")
    _require(-1.0 <= float(event["score"]) <= 1.0, "score must be normalized to [-1, 1]")
    _require(isinstance(event["confidence"], int | float), "confidence must be numeric")
    _require(0.0 <= float(event["confidence"]) <= 1.0, "confidence must be normalized to [0, 1]")

    raw = event["raw"]
    _require(isinstance(raw, dict), "raw must be an object")
    _require(raw.get("sanitized") is True, "raw.sanitized must be true")
    for field in ("bull_hits", "bear_hits", "chars"):
        _require(isinstance(raw.get(field), int), f"raw.{field} must be an integer")
        _require(raw[field] >= 0, f"raw.{field} must be non-negative")
    _require(raw["bull_hits"] + raw["bear_hits"] > 0, "raw hit counts must include polarized language")
    _require(raw["chars"] > 0, "raw.chars must be positive")

    expected_score = round((raw["bull_hits"] - raw["bear_hits"]) / (raw["bull_hits"] + raw["bear_hits"]), 4)
    _require(float(event["score"]) == expected_score, "score must match raw bull/bear count normalization")

    missing_time_fields = [field for field in REQUIRED_TIME_FIELDS if field not in event]
    provenance = fixture.get("provenance")
    provenance_raw_ref = provenance.get("raw_ref") if isinstance(provenance, dict) else None
    raw_ref = event.get("raw_ref") or fixture.get("raw_ref") or provenance_raw_ref

    return {
        "entity": event["entity"],
        "entity_type": event["entity_type"],
        "score": float(event["score"]),
        "confidence": float(event["confidence"]),
        "source": event["source"],
        "venue": event["venue"],
        "raw_counts": {
            "bull_hits": raw["bull_hits"],
            "bear_hits": raw["bear_hits"],
            "chars": raw["chars"],
        },
        "missing_time_fields": missing_time_fields,
        "raw_ref": raw_ref,
    }


def _validate_raw_reference(fixture_path: Path, event_summary: dict[str, Any]) -> dict[str, Any]:
    raw_ref = event_summary["raw_ref"]
    candidate_paths: list[Path] = []
    if isinstance(raw_ref, str) and raw_ref:
        raw_path_text = raw_ref.split("#", 1)[0]
        candidate_paths.append(REPO_ROOT / raw_path_text)

    fallback_path = REPO_ROOT / "runs" / "sentiment" / "raw" / EXPECTED_SOURCE / "NVDA_2026-06-26T10.txt"
    if fallback_path not in candidate_paths:
        candidate_paths.append(fallback_path)

    existing_paths = [path for path in candidate_paths if path.exists()]
    _require(existing_paths, "observed fixture must have an available raw/provenance reference")
    raw_path = existing_paths[0]
    raw_text = raw_path.read_text()
    _require(len(raw_text) == event_summary["raw_counts"]["chars"],
             "raw reference character count must match normalized_event.raw.chars")

    return {
        "raw_ref_present_in_event": isinstance(raw_ref, str) and bool(raw_ref),
        "raw_reference_path": _repo_relative(raw_path),
        "raw_reference_chars": len(raw_text),
    }


def _source_weight_compatibility(event_summary: dict[str, Any]) -> dict[str, Any]:
    source_key = f"{event_summary['source']}::{event_summary['venue']}"
    if event_summary["missing_time_fields"]:
        reason = (
            "Single observed fixture is schema-compatible with source/venue grouping, "
            "but lacks timestamp fields and enough observed windows for lead-lag or CAP credit."
        )
    else:
        reason = (
            "Single observed fixture is schema-compatible with timestamped source/venue grouping, "
            "but still lacks enough observed windows for lead-lag or CAP credit."
        )

    return {
        "compatible": True,
        "source_key": source_key,
        "event_count_for_learning": 1,
        "leadlag_credit_allowed": False,
        "reason": reason,
    }


def validate_observed_finance_fixture(path: Path = DEFAULT_FIXTURE_PATH) -> dict[str, Any]:
    fixture_path = path.resolve()
    _require(fixture_path.exists(), f"fixture does not exist: {fixture_path}")
    fixture = _load_fixture(fixture_path)
    observed_labeling = _validate_observed_labeling(fixture)
    event_summary = _validate_event_shape(fixture)
    raw_reference = _validate_raw_reference(fixture_path, event_summary)
    source_weight_compatibility = _source_weight_compatibility(event_summary)

    limitations = []
    if event_summary["missing_time_fields"]:
        limitations.append(
            "Current fixture omits RFC-001 timestamp fields "
            f"{event_summary['missing_time_fields']}; no-lookahead ordering and lead-lag credit are not asserted."
        )
    if not raw_reference["raw_ref_present_in_event"]:
        limitations.append(
            "Current fixture relies on the committed raw file path convention because normalized_event.raw_ref is absent."
        )

    return {
        "label": "observed_finance_ticker_sentiment_fixture_validation",
        "mode": "offline_propose_only_no_fetch",
        "fixture_path": _repo_relative(fixture_path),
        "observed_labeling": observed_labeling,
        "event": event_summary,
        "raw_reference": raw_reference,
        "source_weight_compatibility": source_weight_compatibility,
        "limitations": limitations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the sanitized observed finance sentiment fixture offline.")
    parser.add_argument("fixture", nargs="?", type=Path, default=DEFAULT_FIXTURE_PATH)
    args = parser.parse_args()
    result = validate_observed_finance_fixture(args.fixture)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
