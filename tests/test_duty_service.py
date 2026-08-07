"""Tests for :class:`services.duty_service.DutyService`."""

from __future__ import annotations

import pytest

from models.duty_category import DutyCategory
from services.duty_service import DutyService, DutyServiceError
from services.personnel_service import PersonnelService
from tests.conftest import FakeUnitOfWork

personnel_service = PersonnelService()
duty_service = DutyService()


async def _seed_personnel(uow: FakeUnitOfWork, count: int = 15) -> None:
    for i in range(count):
        await personnel_service.add_person(uow, f"Person{i}", has_phone=(i % 2 == 0))


async def test_generate_week_creates_draft(uow: FakeUnitOfWork) -> None:
    await _seed_personnel(uow)
    week = await duty_service.generate_week(uow)
    assert week.week_number == 1
    assert week.published is False

    assignments = await uow.assignments.list_for_week(week.id)
    assert len(assignments) > 0


async def test_generate_week_fails_without_personnel(uow: FakeUnitOfWork) -> None:
    with pytest.raises(DutyServiceError):
        await duty_service.generate_week(uow)


async def test_regenerate_replaces_assignments(uow: FakeUnitOfWork) -> None:
    await _seed_personnel(uow)
    week = await duty_service.generate_week(uow)
    first_assignments = await uow.assignments.list_for_week(week.id)

    regenerated = await duty_service.generate_week(uow, week_number=week.week_number)
    assert regenerated.id == week.id
    second_assignments = await uow.assignments.list_for_week(week.id)
    assert len(second_assignments) == len(first_assignments)


async def test_cancel_draft_removes_week(uow: FakeUnitOfWork) -> None:
    await _seed_personnel(uow)
    week = await duty_service.generate_week(uow)
    await duty_service.cancel_draft(uow, week.week_number)
    assert await uow.weeks.get_by_number(week.week_number) is None


async def test_render_week_returns_none_for_missing_week(uow: FakeUnitOfWork) -> None:
    assert await duty_service.render_week(uow, 999) is None


async def test_generated_week_covers_every_active_person_exactly_once(uow: FakeUnitOfWork) -> None:
    await _seed_personnel(uow, count=20)
    week = await duty_service.generate_week(uow)
    assignments = await uow.assignments.list_for_week(week.id)

    person_ids = [a.person_id for a in assignments]
    assert len(person_ids) == len(set(person_ids))

    active_people = await personnel_service.list_active(uow)
    assert len(person_ids) == len(active_people)


async def test_safety_store_group_size(uow: FakeUnitOfWork) -> None:
    await _seed_personnel(uow, count=15)
    week = await duty_service.generate_week(uow)
    assignments = await uow.assignments.list_for_week(week.id)
    safety_store_people = [a for a in assignments if a.category == DutyCategory.SAFETY_STORE]
    assert len(safety_store_people) == 3
