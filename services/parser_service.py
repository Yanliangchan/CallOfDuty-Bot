"""Parses pasted historical duty rosters into structured data.

The parser is deliberately forgiving of blank lines, casing, and minor
spacing differences, but requires the ``Label: Name1, Name2`` shape for
trash/ration lines so that mistakes can be pinpointed precisely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from models.duty_category import DutyCategory

_WEEK_RE = re.compile(r"^week\s+(\d+)\b", re.IGNORECASE)
_BREAKFAST_RE = re.compile(r"^breakfast\s*:?\s*$", re.IGNORECASE)
_LUNCH_RE = re.compile(r"^lunch\s*:?\s*$", re.IGNORECASE)
_DINNER_RE = re.compile(r"^dinner\s*:?\s*$", re.IGNORECASE)
_NO_RATION_RE = re.compile(r"^no\s+ration\b", re.IGNORECASE)

_TRASH_RE = re.compile(r"^throw\s+trash\s*:\s*(.+)$", re.IGNORECASE)
_TRASH_PREFIX_RE = re.compile(r"^throw\s+trash\b", re.IGNORECASE)

_RATION_RE = re.compile(r"^get\s*/?\s*return\s+ration\s*:\s*(.+)$", re.IGNORECASE)
_RATION_PREFIX_RE = re.compile(r"^get\s*/?\s*return\s+ration\b", re.IGNORECASE)

_SAFETY_RE = re.compile(r"^safety\s+stores?\s*:?\s*(.*)$", re.IGNORECASE)
_KEY_DUTY_RE = re.compile(r"^key\s+duty\s*:?\s*(.*)$", re.IGNORECASE)
_RESTING_RE = re.compile(r"^resting\s*:?\s*(.*)$", re.IGNORECASE)

_FREE_SECTION_PATTERNS: tuple[tuple[re.Pattern[str], DutyCategory], ...] = (
    (_SAFETY_RE, DutyCategory.SAFETY_STORE),
    (_KEY_DUTY_RE, DutyCategory.KEY_DUTY),
    (_RESTING_RE, DutyCategory.RESTING),
)


class DutyParseError(Exception):
    """Raised when a pasted duty roster cannot be parsed.

    Carries the offending line number and text so the caller can present a
    precise, actionable error message to the admin.
    """

    def __init__(self, line_number: int, line_text: str, expected: str) -> None:
        self.line_number = line_number
        self.line_text = line_text
        self.expected = expected
        super().__init__(
            f"Unable to parse line {line_number}: {line_text!r}. Expected: {expected}"
        )


@dataclass(slots=True)
class ParsedDuty:
    """A fully parsed historical duty roster, with raw name strings."""

    week_number: int
    assignments: dict[DutyCategory, list[str]] = field(default_factory=dict)

    def names_for(self, category: DutyCategory) -> list[str]:
        return self.assignments.get(category, [])

    def all_names(self) -> set[str]:
        names: set[str] = set()
        for values in self.assignments.values():
            names.update(values)
        return names


def _split_names(raw: str) -> list[str]:
    return [name.strip() for name in raw.split(",") if name.strip()]


def parse_duty_text(text: str) -> ParsedDuty:
    """Parse pasted duty roster text into a :class:`ParsedDuty`.

    Raises :class:`DutyParseError` on the first unrecognisable line,
    identifying exactly which line failed and what was expected.
    """
    raw_lines = text.splitlines()
    week_number: int | None = None
    assignments: dict[DutyCategory, list[str]] = {}

    current_meal: str | None = None  # "breakfast" | "lunch" | "dinner"
    current_free_section: DutyCategory | None = None

    for index, raw_line in enumerate(raw_lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        week_match = _WEEK_RE.match(line)
        if week_match:
            week_number = int(week_match.group(1))
            current_meal = None
            current_free_section = None
            continue

        if _BREAKFAST_RE.match(line):
            current_meal = "breakfast"
            current_free_section = None
            continue
        if _LUNCH_RE.match(line):
            current_meal = "lunch"
            current_free_section = None
            continue
        if _DINNER_RE.match(line):
            current_meal = "dinner"
            current_free_section = None
            continue
        if _NO_RATION_RE.match(line):
            continue

        free_section_match = _match_free_section(line)
        if free_section_match is not None:
            category, inline_names = free_section_match
            current_meal = None
            current_free_section = category
            if inline_names:
                assignments.setdefault(category, []).extend(_split_names(inline_names))
            continue

        trash_match = _TRASH_RE.match(line)
        if trash_match:
            category = _trash_category(current_meal, index, line)
            assignments.setdefault(category, []).extend(_split_names(trash_match.group(1)))
            continue
        if _TRASH_PREFIX_RE.match(line):
            raise DutyParseError(index, raw_line.strip(), "Throw trash: Name1, Name2")

        ration_match = _RATION_RE.match(line)
        if ration_match:
            category = _ration_category(current_meal, index, line)
            assignments.setdefault(category, []).extend(_split_names(ration_match.group(1)))
            continue
        if _RATION_PREFIX_RE.match(line):
            raise DutyParseError(index, raw_line.strip(), "Get/Return ration: Name1, Name2")

        if current_free_section is not None:
            assignments.setdefault(current_free_section, []).extend(_split_names(line))
            continue

        raise DutyParseError(
            index,
            raw_line.strip(),
            "a recognised section header (Breakfast/Lunch/Dinner/Safety stores/Key duty/Resting) "
            "or a 'Label: Name1, Name2' line",
        )

    if week_number is None:
        raise DutyParseError(1, raw_lines[0].strip() if raw_lines else "", "Week <number> Duty")

    return ParsedDuty(week_number=week_number, assignments=assignments)


def _match_free_section(line: str) -> tuple[DutyCategory, str] | None:
    for pattern, category in _FREE_SECTION_PATTERNS:
        match = pattern.match(line)
        if match:
            return category, match.group(1).strip()
    return None


def _trash_category(current_meal: str | None, line_number: int, line: str) -> DutyCategory:
    mapping = {
        "breakfast": DutyCategory.BREAKFAST_TRASH,
        "lunch": DutyCategory.LUNCH_TRASH,
        "dinner": DutyCategory.DINNER_TRASH,
    }
    if current_meal not in mapping:
        raise DutyParseError(line_number, line, "a 'Throw trash' line under Breakfast, Lunch, or Dinner")
    return mapping[current_meal]


def _ration_category(current_meal: str | None, line_number: int, line: str) -> DutyCategory:
    mapping = {
        "lunch": DutyCategory.LUNCH_RATION,
        "dinner": DutyCategory.DINNER_RATION,
    }
    if current_meal not in mapping:
        raise DutyParseError(
            line_number, line, "a 'Get/Return ration' line under Lunch or Dinner (Breakfast has no ration)"
        )
    return mapping[current_meal]
