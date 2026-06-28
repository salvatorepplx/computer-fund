"""Offline validator for PROPOSED artifacts.

This module is intentionally stdlib-only and connector-free. It validates the
repo-as-typed-API handoff into ``runs/PROPOSED/`` without fetching live market
data, touching broker/account state, or authorizing execution. It supports two
writer profiles:

- ``writer=teammate``: offline/simulated proposals authored by sal-bot.
- ``writer=computer``: Computer-generated propose-only artifacts from its own
  validated pipeline, still before ARMED/execution ownership changes.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
PROPOSED_SCHEMA_VERSION = "cf.integration.v1"
PROPOSED_STATE = "PROPOSED"
PROPOSED_ARTIFACT_TYPE = "proposal"
PROPOSED_WRITERS = {"teammate", "computer"}
TEAMMATE_WRITER = "teammate"
COMPUTER_WRITER = "computer"
PROPOSED_OWNER = "computer"
REQUIRED_NON_AUTHORIZATIONS = {"no_order", "no_sizing", "no_execution_instruction"}
ALLOWED_LIVE_CHECKS = {
    "quote_snapshot",
    "account_safety_review",
    "sentiment_capture_refresh",
    "kill_switch_review",
    "kill_switch_status",
    "charter_review",
}
REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "artifact_id",
    "artifact_type",
    "state",
    "created_at",
    "writer",
    "owner",
    "simulated",
    "payload",
}
TEAMMATE_REQUIRED_TOP_LEVEL_FIELDS = REQUIRED_TOP_LEVEL_FIELDS | {"provenance", "validation"}
COMPUTER_REQUIRED_TOP_LEVEL_FIELDS = REQUIRED_TOP_LEVEL_FIELDS
REQUIRED_PAYLOAD_FIELDS = {
    "thesis",
    "entities",
    "dossier_refs",
    "requested_live_checks",
    "non_authorizations",
    "open_risks",
}
TEAMMATE_REQUIRED_PAYLOAD_FIELDS = REQUIRED_PAYLOAD_FIELDS | {"offline_eval_refs"}
COMPUTER_REQUIRED_PAYLOAD_FIELDS = REQUIRED_PAYLOAD_FIELDS | {"conviction", "conviction_components", "signal_provenance"}
ALLOWED_TOP_LEVEL_FIELDS = REQUIRED_TOP_LEVEL_FIELDS | {"provenance", "validation"}
TEAMMATE_ALLOWED_PAYLOAD_FIELDS = TEAMMATE_REQUIRED_PAYLOAD_FIELDS | {"tags", "time_horizon", "expected_falsifiers"}
COMPUTER_ALLOWED_PAYLOAD_FIELDS = COMPUTER_REQUIRED_PAYLOAD_FIELDS | {"tags", "time_horizon", "expected_falsifiers"}
COMPUTER_ONLY_STATES = {"ARMED", "EXECUTED", "CLOSED", "KILLED"}
EXECUTION_AUTHORIZING_KEYS = {
    "account",
    "account_id",
    "account_number",
    "allocation",
    "amount",
    "asset_class",
    "broker",
    "buy",
    "cash",
    "contract",
    "dollar_amount",
    "execution",
    "execution_intent",
    "limit_price",
    "market_order",
    "notional",
    "option_premium_at_risk",
    "order",
    "order_id",
    "order_type",
    "place_args",
    "premium",
    "price",
    "quantity",
    "reviewed_order",
    "route",
    "sell",
    "share_count",
    "shares",
    "side",
    "size",
    "sizing",
    "strike",
    "target_allocation",
    "target_price",
    "ticker_price",
    "trade",
    "trigger_price",
}
EXECUTION_AUTHORIZING_PHRASES = (
    "authorize execution",
    "authorized to execute",
    "execute this trade",
    "place order",
    "place the order",
    "route order",
    "submit order",
    "buy ",
    "sell ",
    "shares",
    "contracts",
    "target allocation",
    "position size",
)
ISO8601_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")
ARTIFACT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ENTITY_RE = re.compile(r"^[A-Z_]+:[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str

    def format(self) -> str:
        return f"{self.path}: {self.message}"


class ProposedValidationError(ValueError):
    """Raised when one or more PROPOSED artifacts fail validation."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.format() for issue in self.issues))


def validate_proposed_artifact(artifact: dict[str, Any], *, source_path: str = "<artifact>") -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    writer = artifact.get("writer")
    required_top_level_fields = TEAMMATE_REQUIRED_TOP_LEVEL_FIELDS if writer == TEAMMATE_WRITER else COMPUTER_REQUIRED_TOP_LEVEL_FIELDS
    _validate_required_keys(artifact, required_top_level_fields, source_path, issues)
    _validate_allowed_keys(artifact, ALLOWED_TOP_LEVEL_FIELDS, source_path, issues)

    _require_equal(artifact, "schema_version", PROPOSED_SCHEMA_VERSION, source_path, issues)
    _require_equal(artifact, "artifact_type", PROPOSED_ARTIFACT_TYPE, source_path, issues)
    _require_equal(artifact, "state", PROPOSED_STATE, source_path, issues)
    if writer not in PROPOSED_WRITERS:
        issues.append(ValidationIssue(f"{source_path}.writer", f"must be one of {sorted(PROPOSED_WRITERS)}"))
    _require_equal(artifact, "owner", PROPOSED_OWNER, source_path, issues)
    if artifact.get("state") in COMPUTER_ONLY_STATES:
        issues.append(ValidationIssue(f"{source_path}.state", "Computer-owned states are not valid Teammate proposals"))
    _validate_writer_simulation_label(writer, artifact.get("simulated"), source_path, issues)
    if not _is_non_empty_string(artifact.get("artifact_id")) or not ARTIFACT_ID_RE.match(str(artifact.get("artifact_id", ""))):
        issues.append(ValidationIssue(f"{source_path}.artifact_id", "must be a non-empty filesystem-safe identifier"))
    if not _is_non_empty_string(artifact.get("created_at")) or not ISO8601_UTC_RE.match(str(artifact.get("created_at", ""))):
        issues.append(ValidationIssue(f"{source_path}.created_at", "must be UTC ISO8601 like 2026-06-26T00:00:00Z or .123456+00:00"))

    payload = artifact.get("payload")
    if not isinstance(payload, dict):
        issues.append(ValidationIssue(f"{source_path}.payload", "must be an object"))
    else:
        _validate_payload(payload, writer, source_path, issues)
    if writer == TEAMMATE_WRITER:
        _validate_provenance(artifact.get("provenance"), source_path, issues)
        _validate_validation_claims(artifact.get("validation"), source_path, issues)
    else:
        if "provenance" in artifact:
            _validate_provenance(artifact.get("provenance"), source_path, issues)
        if "validation" in artifact:
            _validate_validation_claims(artifact.get("validation"), source_path, issues)

    _reject_execution_authorizing_content(artifact, source_path, issues)
    return issues


def validate_proposed_file(path: Path, *, repo_root: Path = REPO_ROOT) -> list[ValidationIssue]:
    relative_path = _repo_relative(path, repo_root)
    try:
        artifact = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [ValidationIssue(relative_path, f"invalid JSON: {exc.msg}")]
    if not isinstance(artifact, dict):
        return [ValidationIssue(relative_path, "artifact must be a JSON object")]

    issues = validate_proposed_artifact(artifact, source_path=relative_path)
    expected_filename = f"{artifact.get('artifact_id')}.json"
    if _is_non_empty_string(artifact.get("artifact_id")) and path.name != expected_filename:
        issues.append(ValidationIssue(relative_path, f"filename must match artifact_id ({expected_filename})"))
    return issues


def discover_proposed_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(child for child in path.rglob("*.json") if child.is_file()))
        elif path.is_file() and path.suffix == ".json":
            files.append(path)
    return sorted(files)


def validate_proposed_paths(paths: Iterable[Path], *, repo_root: Path = REPO_ROOT) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    path_list = list(paths)
    for path in path_list:
        if not path.exists():
            issues.append(ValidationIssue(_repo_relative(path, repo_root), "path does not exist"))
        elif path.is_file() and path.suffix != ".json":
            issues.append(ValidationIssue(_repo_relative(path, repo_root), "must be a JSON file or directory"))
    for path in discover_proposed_files(path_list):
        issues.extend(validate_proposed_file(path, repo_root=repo_root))
    return issues


def assert_valid_proposed_paths(paths: Iterable[Path], *, repo_root: Path = REPO_ROOT) -> None:
    issues = validate_proposed_paths(paths, repo_root=repo_root)
    if issues:
        raise ProposedValidationError(issues)


def _validate_writer_simulation_label(writer: Any, simulated: Any, source_path: str, issues: list[ValidationIssue]) -> None:
    if writer == TEAMMATE_WRITER and simulated is not True:
        issues.append(ValidationIssue(f"{source_path}.simulated", "Teammate proposals must be labeled simulated=true/offline"))
    elif writer == COMPUTER_WRITER and simulated is not False:
        issues.append(ValidationIssue(f"{source_path}.simulated", "Computer pipeline proposals must be labeled simulated=false"))
    elif writer not in PROPOSED_WRITERS and not isinstance(simulated, bool):
        issues.append(ValidationIssue(f"{source_path}.simulated", "must be a boolean"))


def _validate_payload(payload: dict[str, Any], writer: Any, source_path: str, issues: list[ValidationIssue]) -> None:
    payload_path = f"{source_path}.payload"
    required_fields = TEAMMATE_REQUIRED_PAYLOAD_FIELDS if writer == TEAMMATE_WRITER else COMPUTER_REQUIRED_PAYLOAD_FIELDS
    allowed_fields = TEAMMATE_ALLOWED_PAYLOAD_FIELDS if writer == TEAMMATE_WRITER else COMPUTER_ALLOWED_PAYLOAD_FIELDS
    _validate_required_keys(payload, required_fields, payload_path, issues)
    _validate_allowed_keys(payload, allowed_fields, payload_path, issues)

    if not _is_non_empty_string(payload.get("thesis")):
        issues.append(ValidationIssue(f"{payload_path}.thesis", "must be a non-empty string"))
    _validate_string_list(payload, "entities", payload_path, issues, min_items=1, pattern=ENTITY_RE)
    _validate_repo_path_list(payload, "dossier_refs", payload_path, issues, min_items=1)
    if writer == TEAMMATE_WRITER or "offline_eval_refs" in payload:
        _validate_repo_path_list(payload, "offline_eval_refs", payload_path, issues, min_items=1)
    _validate_string_list(payload, "requested_live_checks", payload_path, issues, min_items=1, allowed=ALLOWED_LIVE_CHECKS)
    _validate_string_list(payload, "non_authorizations", payload_path, issues, min_items=len(REQUIRED_NON_AUTHORIZATIONS))
    _validate_string_list(payload, "open_risks", payload_path, issues, min_items=1)
    _validate_string_list(payload, "tags", payload_path, issues, min_items=0, required=False)
    _validate_string_list(payload, "expected_falsifiers", payload_path, issues, min_items=0, required=False)
    if writer == COMPUTER_WRITER:
        _validate_computer_pipeline_payload(payload, payload_path, issues)

    non_authorizations = payload.get("non_authorizations")
    if isinstance(non_authorizations, list):
        missing = sorted(REQUIRED_NON_AUTHORIZATIONS - set(non_authorizations))
        if missing:
            issues.append(ValidationIssue(f"{payload_path}.non_authorizations", f"missing required markers: {missing}"))


def _validate_computer_pipeline_payload(payload: dict[str, Any], payload_path: str, issues: list[ValidationIssue]) -> None:
    conviction = payload.get("conviction")
    if not isinstance(conviction, (int, float)) or not 0 <= conviction <= 1:
        issues.append(ValidationIssue(f"{payload_path}.conviction", "must be a number between 0 and 1"))
    if not isinstance(payload.get("conviction_components"), dict) or not payload.get("conviction_components"):
        issues.append(ValidationIssue(f"{payload_path}.conviction_components", "must be a non-empty object"))
    signal_provenance = payload.get("signal_provenance")
    if not isinstance(signal_provenance, dict):
        issues.append(ValidationIssue(f"{payload_path}.signal_provenance", "must be an object"))
        return
    for key in ("verdict", "best_lag", "best_corr", "circular", "source"):
        if key not in signal_provenance:
            issues.append(ValidationIssue(f"{payload_path}.signal_provenance", f"missing required key {key!r}"))


def _validate_provenance(value: Any, source_path: str, issues: list[ValidationIssue]) -> None:
    provenance_path = f"{source_path}.provenance"
    if not isinstance(value, dict):
        issues.append(ValidationIssue(provenance_path, "must be an object"))
        return
    _validate_allowed_keys(value, {"inputs", "raw_refs", "raw_ref_explanation"}, provenance_path, issues)
    _validate_repo_path_list(value, "inputs", provenance_path, issues, min_items=1)
    raw_refs = value.get("raw_refs")
    raw_explanation = value.get("raw_ref_explanation")
    if raw_refs is None and not _is_non_empty_string(raw_explanation):
        issues.append(ValidationIssue(provenance_path, "must include raw_refs or raw_ref_explanation"))
    if raw_refs is not None:
        _validate_repo_path_list(value, "raw_refs", provenance_path, issues, min_items=1)


def _validate_validation_claims(value: Any, source_path: str, issues: list[ValidationIssue]) -> None:
    validation_path = f"{source_path}.validation"
    if not isinstance(value, dict):
        issues.append(ValidationIssue(validation_path, "must be an object"))
        return
    _validate_allowed_keys(value, {"required_checks", "passed_checks"}, validation_path, issues)
    _validate_string_list(value, "required_checks", validation_path, issues, min_items=1)
    _validate_string_list(value, "passed_checks", validation_path, issues, min_items=0)

    required_checks = value.get("required_checks")
    if isinstance(required_checks, list) and "schema" not in required_checks:
        issues.append(ValidationIssue(f"{validation_path}.required_checks", "must include 'schema'"))
    passed_checks = value.get("passed_checks")
    if isinstance(passed_checks, list) and passed_checks:
        issues.append(ValidationIssue(f"{validation_path}.passed_checks", "must stay empty until a committed report proves checks passed"))


def _validate_required_keys(value: dict[str, Any], required: set[str], source_path: str, issues: list[ValidationIssue]) -> None:
    missing = sorted(required - set(value))
    if missing:
        issues.append(ValidationIssue(source_path, f"missing required keys: {missing}"))


def _validate_allowed_keys(value: dict[str, Any], allowed: set[str], source_path: str, issues: list[ValidationIssue]) -> None:
    extras = sorted(set(value) - allowed)
    if extras:
        issues.append(ValidationIssue(source_path, f"unknown keys are not allowed: {extras}"))


def _require_equal(artifact: dict[str, Any], key: str, expected: Any, source_path: str, issues: list[ValidationIssue]) -> None:
    if artifact.get(key) != expected:
        issues.append(ValidationIssue(f"{source_path}.{key}", f"must be {expected!r}"))


def _validate_string_list(
    payload: dict[str, Any],
    key: str,
    source_path: str,
    issues: list[ValidationIssue],
    *,
    min_items: int,
    required: bool = True,
    allowed: set[str] | None = None,
    pattern: re.Pattern[str] | None = None,
) -> None:
    if key not in payload and not required:
        return
    value = payload.get(key)
    value_path = f"{source_path}.{key}"
    if not isinstance(value, list) or len(value) < min_items:
        issues.append(ValidationIssue(value_path, f"must be a list with at least {min_items} item(s)"))
        return
    for index, item in enumerate(value):
        item_path = f"{value_path}[{index}]"
        if not _is_non_empty_string(item):
            issues.append(ValidationIssue(item_path, "must be a non-empty string"))
            continue
        if allowed is not None and item not in allowed:
            issues.append(ValidationIssue(item_path, f"unsupported value {item!r}"))
        if pattern is not None and not pattern.match(item):
            issues.append(ValidationIssue(item_path, f"does not match required pattern {pattern.pattern!r}"))


def _validate_repo_path_list(payload: dict[str, Any], key: str, source_path: str, issues: list[ValidationIssue], *, min_items: int) -> None:
    _validate_string_list(payload, key, source_path, issues, min_items=min_items)
    value = payload.get(key)
    if not isinstance(value, list):
        return
    for index, item in enumerate(value):
        if not isinstance(item, str):
            continue
        if item.startswith("/") or ".." in Path(item).parts:
            issues.append(ValidationIssue(f"{source_path}.{key}[{index}]", "must be a repo-relative path without traversal"))


def _reject_execution_authorizing_content(value: Any, source_path: str, issues: list[ValidationIssue]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{source_path}.{key}"
            normalized_key = _normalize_key(key)
            if normalized_key in EXECUTION_AUTHORIZING_KEYS:
                issues.append(ValidationIssue(child_path, "execution-authorizing fields are Computer-only"))
            _reject_execution_authorizing_content(child, child_path, issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_execution_authorizing_content(child, f"{source_path}[{index}]", issues)
    elif isinstance(value, str):
        normalized_value = f" {value.lower()} "
        for phrase in EXECUTION_AUTHORIZING_PHRASES:
            if phrase in normalized_value:
                issues.append(ValidationIssue(source_path, f"execution-authorizing phrase is not allowed: {phrase.strip()!r}"))
                break


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate offline PROPOSED artifacts")
    parser.add_argument("paths", nargs="*", default=["runs/PROPOSED"], help="JSON files or directories to validate")
    args = parser.parse_args(argv)

    paths = [Path(path) for path in args.paths]
    issues = validate_proposed_paths(paths)
    if issues:
        for issue in issues:
            print(issue.format())
        return 1

    print(f"validated {len(discover_proposed_files(paths))} PROPOSED artifact(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
