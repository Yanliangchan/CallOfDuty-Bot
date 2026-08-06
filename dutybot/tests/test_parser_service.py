"""Tests for the historical duty roster text parser."""

from __future__ import annotations

import pytest

from models.duty_category import DutyCategory
from services.parser_service import DutyParseError, parse_duty_text

SAMPLE_INPUT = """
Week 6 Duty

Breakfast

Throw trash: Ernest, Yan Liang

No ration to collect

Lunch

Throw trash: Yu Jun, Dylan

Get/Return ration: Yeo Dan, Kalyaan

Dinner

Throw trash: Jasfer, Jonathan

Get/Return ration: Jia Ming, Ryan

Safety stores:

Brayden, Jayson, Jia Jie, Noah

Key duty:

Shawn, Aloysius

Resting:

Andrew, Matthew, Javier
"""


def test_parses_week_number() -> None:
    parsed = parse_duty_text(SAMPLE_INPUT)
    assert parsed.week_number == 6


def test_parses_all_categories() -> None:
    parsed = parse_duty_text(SAMPLE_INPUT)
    assert parsed.names_for(DutyCategory.BREAKFAST_TRASH) == ["Ernest", "Yan Liang"]
    assert parsed.names_for(DutyCategory.LUNCH_TRASH) == ["Yu Jun", "Dylan"]
    assert parsed.names_for(DutyCategory.LUNCH_RATION) == ["Yeo Dan", "Kalyaan"]
    assert parsed.names_for(DutyCategory.DINNER_TRASH) == ["Jasfer", "Jonathan"]
    assert parsed.names_for(DutyCategory.DINNER_RATION) == ["Jia Ming", "Ryan"]
    assert parsed.names_for(DutyCategory.SAFETY_STORE) == ["Brayden", "Jayson", "Jia Jie", "Noah"]
    assert parsed.names_for(DutyCategory.KEY_DUTY) == ["Shawn", "Aloysius"]
    assert parsed.names_for(DutyCategory.RESTING) == ["Andrew", "Matthew", "Javier"]


def test_ignores_extra_blank_lines() -> None:
    padded = "\n\n\n" + SAMPLE_INPUT.replace("\n\n", "\n\n\n\n")
    parsed = parse_duty_text(padded)
    assert parsed.week_number == 6
    assert parsed.names_for(DutyCategory.BREAKFAST_TRASH) == ["Ernest", "Yan Liang"]


def test_accepts_case_and_spacing_variations() -> None:
    text = """
    WEEK 9 Duty

    breakfast
    THROW TRASH:   Alice ,   Bob

    lunch
    Throw Trash: Carl, Dave
    get / return ration: Eve, Frank
    """
    parsed = parse_duty_text(text)
    assert parsed.week_number == 9
    assert parsed.names_for(DutyCategory.BREAKFAST_TRASH) == ["Alice", "Bob"]
    assert parsed.names_for(DutyCategory.LUNCH_RATION) == ["Eve", "Frank"]


def test_missing_colon_raises_parse_error_with_line_number() -> None:
    text = "Week 6 Duty\n\nBreakfast\n\nThrow trash Ernest Yan Liang\n"
    with pytest.raises(DutyParseError) as exc_info:
        parse_duty_text(text)
    error = exc_info.value
    assert error.line_number == 5
    assert "Ernest" in error.line_text
    assert "Throw trash: Name1, Name2" in error.expected


def test_ration_under_breakfast_raises_error() -> None:
    text = "Week 6 Duty\n\nBreakfast\n\nGet/Return ration: Alice, Bob\n"
    with pytest.raises(DutyParseError):
        parse_duty_text(text)


def test_missing_week_number_raises_error() -> None:
    with pytest.raises(DutyParseError):
        parse_duty_text("Breakfast\n\nThrow trash: Alice, Bob\n")
