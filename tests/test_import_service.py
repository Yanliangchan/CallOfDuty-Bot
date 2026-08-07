"""Tests for :class:`services.import_service.ImportService`."""

from __future__ import annotations

from models.duty_category import DutyCategory
from services.import_service import ImportService
from services.parser_service import parse_duty_text
from services.personnel_service import PersonnelService
from tests.conftest import FakeUnitOfWork

personnel_service = PersonnelService()
import_service = ImportService()

SAMPLE = """
Week 6 Duty

Breakfast

Throw trash: Ernest, Yan Liang

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


async def test_resolve_names_flags_unknown_people(uow: FakeUnitOfWork) -> None:
    await personnel_service.add_person(uow, "Ernest")
    parsed = parse_duty_text(SAMPLE)

    resolution = await import_service.resolve_names(uow, parsed)

    assert "Ernest" in resolution.known
    assert "Yan Liang" in resolution.unknown
    assert "Dylan" in resolution.unknown


async def test_save_import_never_silently_creates_duplicates(uow: FakeUnitOfWork) -> None:
    ernest = await personnel_service.add_person(uow, "Ernest")
    parsed = parse_duty_text("Week 1 Duty\n\nBreakfast\n\nThrow trash: Ernest, Yan Liang\n")

    # "Yan Liang" is deliberately ignored (not resolved) rather than auto-created.
    week = await import_service.save_import(uow, parsed, {"Ernest": ernest})

    all_people = await personnel_service.list_active(uow)
    assert len(all_people) == 1
    assert all_people[0].name == "Ernest"

    assignments = await uow.assignments.list_for_week(week.id)
    trash_assignees = [a for a in assignments if a.category == DutyCategory.BREAKFAST_TRASH]
    assert len(trash_assignees) == 1
    assert trash_assignees[0].person_id == ernest.id
