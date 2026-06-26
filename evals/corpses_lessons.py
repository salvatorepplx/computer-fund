"""Offline validation for the CORPSES and lessons discipline.

This module reads only committed Markdown process artifacts. It does not touch
broker connectors, live market data, account/order state, ARMED artifacts,
execution placement, or sizing behavior.
"""
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CORPSES_PATH = REPO_ROOT / "runs" / "CORPSES.md"
LESSONS_PATH = REPO_ROOT / "corpus" / "lessons.md"

CORPSE_REQUIRED_FIELDS = (
    "Status",
    "Evidence type",
    "Thesis",
    "Kill reason",
    "Lesson",
    "Seeder feedback",
    "Reopen criteria",
)
LESSON_REQUIRED_FIELDS = (
    "Source corpse",
    "Reusable lesson",
    "Seeder rule",
    "Meta/eval linkage",
    "Revisit trigger",
)


def _has_field(markdown: str, field: str) -> bool:
    return bool(re.search(rf"^- \*\*{re.escape(field)}\*\*:", markdown, re.MULTILINE))


def _missing_fields(markdown: str, required_fields: tuple[str, ...]) -> list[str]:
    return [field for field in required_fields if not _has_field(markdown, field)]


def _count_entries(markdown: str) -> int:
    return len(re.findall(r"^### \d{4}-\d{2}-\d{2} — ", markdown, re.MULTILINE))


def validate_corpses_lessons() -> dict[str, object]:
    corpses_markdown = CORPSES_PATH.read_text(encoding="utf-8")
    lessons_markdown = LESSONS_PATH.read_text(encoding="utf-8")

    return {
        "label": "corpses_lessons_offline_discipline_validation",
        "mode": "offline_propose_only_markdown_only",
        "paths": [str(CORPSES_PATH.relative_to(REPO_ROOT)), str(LESSONS_PATH.relative_to(REPO_ROOT))],
        "corpses": {
            "entry_count": _count_entries(corpses_markdown),
            "missing_required_fields": _missing_fields(corpses_markdown, CORPSE_REQUIRED_FIELDS),
            "has_seeder_feedback_rules": "## Seeder Feedback Rules" in corpses_markdown,
            "forbids_live_execution_touchpoints": "must not touch Robinhood" in corpses_markdown,
        },
        "lessons": {
            "entry_count": _count_entries(lessons_markdown),
            "missing_required_fields": _missing_fields(lessons_markdown, LESSON_REQUIRED_FIELDS),
            "links_corpses": "runs/CORPSES.md" in lessons_markdown,
            "links_meta_orchestrator": "memory_lessons" in lessons_markdown,
            "forbids_live_execution_touchpoints": "must not touch Robinhood" in lessons_markdown,
        },
    }


def main() -> int:
    import json

    print(json.dumps(validate_corpses_lessons(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
