"""Tests for duty roster message rendering."""

from __future__ import annotations

from models.duty_assignment import DutyAssignment
from models.duty_category import DutyCategory
from models.personnel import Personnel
from utils.formatting import render_week_roster


def _assignment(category: DutyCategory, person: Personnel) -> DutyAssignment:
    return DutyAssignment(category=category, meal=category.meal, person=person, person_id=person.id or 0)


def test_render_week_roster_includes_phone_marker() -> None:
    ernest = Personnel(id=1, name="Ernest", has_phone=True)
    yan_liang = Personnel(id=2, name="Yan Liang", has_phone=False)
    assignments = [
        _assignment(DutyCategory.BREAKFAST_TRASH, ernest),
        _assignment(DutyCategory.BREAKFAST_TRASH, yan_liang),
    ]

    text = render_week_roster(6, assignments)

    assert "Week 6 Duty" in text
    assert "Ernest 📱" in text
    assert "Yan Liang" in text
    assert "Yan Liang 📱" not in text


def test_render_week_roster_shows_no_ration_when_absent() -> None:
    ernest = Personnel(id=1, name="Ernest", has_phone=False)
    assignments = [_assignment(DutyCategory.BREAKFAST_TRASH, ernest)]

    text = render_week_roster(6, assignments)

    assert "No ration" in text


def test_render_week_roster_lists_resting_as_none_when_empty() -> None:
    text = render_week_roster(1, [])
    assert "Resting" in text
    assert "None" in text
