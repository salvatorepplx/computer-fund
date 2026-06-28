"""Offline KG replay diagnostic for a frozen observed sentiment fixture.

This diagnostic is connector-free and propose-only. It reads the sanitized
static observed series JSONL fixture, replays it into a temporary
KnowledgeGraph, and verifies observed rows remain non-simulated while preserving
available timestamp/provenance fields. It does not call live adapters, broker
APIs, market data, account state, orders, sizing, or ARMED/EXECUTED handoffs.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from graph.kg import KnowledgeGraph

STATE_GRAPH_PATH = REPO_ROOT / "state" / "knowledge_graph.json"
DEFAULT_SERIES_PATH = REPO_ROOT / "evals" / "fixtures" / "kg_observed_series_nvda.jsonl"
EXPECTED_ENTITY = "TICKER:NVDA"
EXPECTED_SOURCE = "finance_ticker_sentiment"
EXPECTED_ROW_COUNT = 3
EXPECTED_LATEST_EVENT_ID = "sha256:88c1a4c35775620d"
EXPECTED_LATEST_SCORE = 0.5
EXPECTED_MOMENTUM = 0.8333
REQUIRED_FIELDS = ("captured_at", "entity", "score", "confidence", "source", "ts", "event_id")
MIN_SERIES_ROWS_FOR_READINESS = 20


class KGObservedSeriesDiagnosticError(AssertionError):
    """Raised when committed observed sentiment series cannot replay into KG."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise KGObservedSeriesDiagnosticError(message)


def _repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def _load_series(path: Path) -> list[dict[str, Any]]:
    _require(path.exists(), f"series file does not exist: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:  # pragma: no cover - surfaced by CLI/harness
            raise KGObservedSeriesDiagnosticError(f"line {line_number} must parse as JSON: {exc}") from exc
        _require(isinstance(row, dict), f"line {line_number} must be a JSON object")
        row["_line_number"] = line_number
        rows.append(row)
    _require(rows, "series must contain at least one observed row")
    return rows


def _validate_row(row: dict[str, Any], prior_ts: str | None) -> str:
    line_number = row["_line_number"]
    missing = [field for field in REQUIRED_FIELDS if field not in row]
    _require(not missing, f"line {line_number} missing required fields: {missing}")
    _require(row["entity"] == EXPECTED_ENTITY, f"line {line_number} entity must be {EXPECTED_ENTITY}")
    _require(row["source"] == EXPECTED_SOURCE, f"line {line_number} source must be {EXPECTED_SOURCE}")
    _require(isinstance(row["score"], int | float), f"line {line_number} score must be numeric")
    _require(-1.0 <= float(row["score"]) <= 1.0, f"line {line_number} score must be normalized")
    _require(isinstance(row["confidence"], int | float), f"line {line_number} confidence must be numeric")
    _require(0.0 <= float(row["confidence"]) <= 1.0, f"line {line_number} confidence must be normalized")
    _require(str(row["event_id"]).startswith("sha256:"), f"line {line_number} event_id must carry provenance hash")
    _require(row.get("simulated") is not True, f"line {line_number} observed series must not set simulated=true")
    ts = str(row["ts"])
    _require("T" in ts and "+00:00" in ts, f"line {line_number} ts must be timezone-aware ISO text")
    captured_at = str(row["captured_at"])
    _require("T" in captured_at and "+00:00" in captured_at,
             f"line {line_number} captured_at must be timezone-aware ISO text")
    if prior_ts is not None:
        _require(ts >= prior_ts, f"line {line_number} ts must be monotonically nondecreasing")
    return ts


def run_kg_observed_series_diagnostic(series_path: Path = DEFAULT_SERIES_PATH) -> dict[str, Any]:
    """Replay committed observed sentiment rows into a temp KG and summarize checks."""
    resolved_series_path = series_path.resolve()
    rows = _load_series(resolved_series_path)
    _require(len(rows) == EXPECTED_ROW_COUNT, f"fixture row count must stay frozen at {EXPECTED_ROW_COUNT}")

    prior_ts: str | None = None
    event_ids: set[str] = set()
    for row in rows:
        prior_ts = _validate_row(row, prior_ts)
        _require(row["event_id"] not in event_ids, f"line {row['_line_number']} event_id must be unique")
        event_ids.add(row["event_id"])

    with tempfile.TemporaryDirectory() as tmp_dir:
        graph_path = Path(tmp_dir) / "knowledge_graph.json"
        state_graph_before = STATE_GRAPH_PATH.read_bytes() if STATE_GRAPH_PATH.exists() else None
        kg = KnowledgeGraph(graph_path)
        kg.upsert_node(EXPECTED_ENTITY, "ticker", symbol="NVDA", fixture="observed_series_offline_diagnostic")

        for row in rows:
            kg.add_sentiment(
                EXPECTED_ENTITY,
                row["score"],
                row["confidence"],
                row["source"],
                simulated=False,
                observed_at=row["ts"],
                captured_at=row["captured_at"],
                event_id=row["event_id"],
                price_proxy=row.get("price_proxy"),
            )

        history = kg.sentiment_history(EXPECTED_ENTITY)
        latest = kg.latest_sentiment(EXPECTED_ENTITY)
        momentum = kg.sentiment_momentum(EXPECTED_ENTITY)
        saved_path = kg.save()
        reloaded = KnowledgeGraph(saved_path)
        reloaded_history = reloaded.sentiment_history(EXPECTED_ENTITY)
        temp_graph_path = saved_path.resolve()

    state_graph_after = STATE_GRAPH_PATH.read_bytes() if STATE_GRAPH_PATH.exists() else None

    _require(len(history) == len(rows), "KG sentiment history length must match observed series rows")
    _require(all(entry["simulated"] is False for entry in history), "KG replayed rows must remain simulated:false")
    _require(latest is not None, "KG latest observed sentiment must exist after replay")
    _require(latest["event_id"] == rows[-1]["event_id"], "KG latest observed must be the final observed row")
    expected_momentum = None
    if len(rows) >= 2:
        expected_momentum = round(float(rows[-1]["score"]) - float(rows[-2]["score"]), 4)
    _require(momentum == expected_momentum, "KG momentum must use observed-only replayed history")
    _require(latest["event_id"] == EXPECTED_LATEST_EVENT_ID, "fixture latest event_id must stay frozen")
    _require(latest["score"] == EXPECTED_LATEST_SCORE, "fixture latest score must stay frozen")
    _require(momentum == EXPECTED_MOMENTUM, "fixture observed-only momentum must stay frozen")
    _require(reloaded_history == history, "temp KG save/reload must preserve observed metadata")
    _require(state_graph_after == state_graph_before, "diagnostic must not mutate state/knowledge_graph.json")
    _require(temp_graph_path != STATE_GRAPH_PATH.resolve(), "diagnostic must write only to temp graph state")

    readiness = {
        "ready_for_leadlag_or_current_step_credit": False,
        "observed_row_count": len(rows),
        "minimum_observed_rows": MIN_SERIES_ROWS_FOR_READINESS,
        "reason": (
            "Committed NVDA series is sufficient for KG plumbing and observed/non-simulated checks, "
            "but remains too small and single-source for lead-lag, CAP, or trading readiness credit."
        ),
    }

    return {
        "label": "kg_observed_series_offline_diagnostic",
        "mode": "offline_propose_only_no_fetch_no_trading",
        "series_path": _repo_relative(resolved_series_path),
        "state_graph_mutated": state_graph_after != state_graph_before,
        "temp_graph_used": temp_graph_path != STATE_GRAPH_PATH.resolve(),
        "entity": EXPECTED_ENTITY,
        "source": EXPECTED_SOURCE,
        "row_count": len(rows),
        "required_fields": list(REQUIRED_FIELDS),
        "observed_rows_simulated_flags": [entry["simulated"] for entry in history],
        "latest_observed": {
            "score": latest["score"],
            "confidence": latest["confidence"],
            "source": latest["source"],
            "observed_at": latest["observed_at"],
            "captured_at": latest["captured_at"],
            "event_id": latest["event_id"],
            "simulated": latest["simulated"],
        },
        "momentum": momentum,
        "expected_momentum": expected_momentum,
        "readiness": readiness,
        "limitations": [
            "Uses only a committed static JSONL fixture; no live connector fetches are performed.",
            "Writes only to a TemporaryDirectory KnowledgeGraph and does not mutate state/knowledge_graph.json.",
            "The sample is NVDA-only, source-limited, and below the pre-registered readiness threshold.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a frozen observed sentiment fixture into a temp KG offline.")
    parser.add_argument("series", nargs="?", type=Path, default=DEFAULT_SERIES_PATH)
    args = parser.parse_args()
    result = run_kg_observed_series_diagnostic(args.series)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
