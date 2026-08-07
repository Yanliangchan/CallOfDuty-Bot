"""Tests for :class:`services.personnel_service.PersonnelService`."""

from __future__ import annotations

import pytest

from services.personnel_service import PersonnelService, PersonnelServiceError
from tests.conftest import FakeUnitOfWork

service = PersonnelService()


async def test_add_person_creates_record(uow: FakeUnitOfWork) -> None:
    person = await service.add_person(uow, "Ernest", has_phone=True)
    assert person.id is not None
    assert person.name == "Ernest"
    assert person.has_phone is True


async def test_add_person_rejects_duplicate_name(uow: FakeUnitOfWork) -> None:
    await service.add_person(uow, "Ernest")
    with pytest.raises(PersonnelServiceError):
        await service.add_person(uow, "ernest")


async def test_toggle_phone_flips_state(uow: FakeUnitOfWork) -> None:
    person = await service.add_person(uow, "Dylan", has_phone=False)
    updated = await service.toggle_phone(uow, person.id)
    assert updated.has_phone is True
    updated_again = await service.toggle_phone(uow, person.id)
    assert updated_again.has_phone is False


async def test_set_active_deactivates_person(uow: FakeUnitOfWork) -> None:
    person = await service.add_person(uow, "Kalyaan")
    updated = await service.set_active(uow, person.id, False)
    assert updated.active is False

    active_people = await service.list_active(uow)
    assert all(p.id != person.id for p in active_people)

    inactive_people = await service.list_inactive(uow)
    assert any(p.id == person.id for p in inactive_people)


async def test_rename_rejects_collision(uow: FakeUnitOfWork) -> None:
    await service.add_person(uow, "Ryan")
    second = await service.add_person(uow, "Jonathan")
    with pytest.raises(PersonnelServiceError):
        await service.rename(uow, second.id, "Ryan")


async def test_remove_person_deletes_record(uow: FakeUnitOfWork) -> None:
    person = await service.add_person(uow, "Noah")
    await service.remove_person(uow, person.id)
    assert await service.find_or_none(uow, "Noah") is None
