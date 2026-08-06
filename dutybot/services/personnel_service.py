"""Business logic for managing personnel records."""

from __future__ import annotations

import logging

from database.unit_of_work import UnitOfWorkProtocol
from models.personnel import Personnel

logger = logging.getLogger(__name__)


class PersonnelServiceError(Exception):
    """Raised for user-facing personnel-service failures."""


class PersonnelService:
    """Operations for adding, editing, and querying personnel."""

    async def add_person(
        self, uow: UnitOfWorkProtocol, name: str, *, has_phone: bool = False, remarks: str | None = None
    ) -> Personnel:
        """Add a new person, rejecting duplicate names."""
        name = name.strip()
        if not name:
            raise PersonnelServiceError("Name cannot be empty.")
        existing = await uow.personnel.get_by_name(name)
        if existing is not None:
            raise PersonnelServiceError(f"A person named '{name}' already exists.")
        person = await uow.personnel.add(name, has_phone=has_phone, remarks=remarks)
        logger.info("Added personnel: %s (id=%s)", name, person.id)
        return person

    async def toggle_phone(self, uow: UnitOfWorkProtocol, person_id: int) -> Personnel:
        """Toggle a person's phone-holder status."""
        person = await self._require_person(uow, person_id)
        await uow.personnel.update(person, has_phone=not person.has_phone)
        logger.info("Toggled phone status for %s -> %s", person.name, person.has_phone)
        return person

    async def set_active(self, uow: UnitOfWorkProtocol, person_id: int, active: bool) -> Personnel:
        """Activate or deactivate a person."""
        person = await self._require_person(uow, person_id)
        await uow.personnel.update(person, active=active)
        logger.info("Set active=%s for %s", active, person.name)
        return person

    async def update_remarks(self, uow: UnitOfWorkProtocol, person_id: int, remarks: str) -> Personnel:
        """Update a person's remarks field."""
        person = await self._require_person(uow, person_id)
        await uow.personnel.update(person, remarks=remarks)
        return person

    async def rename(self, uow: UnitOfWorkProtocol, person_id: int, new_name: str) -> Personnel:
        """Rename a person, rejecting a name collision."""
        new_name = new_name.strip()
        if not new_name:
            raise PersonnelServiceError("Name cannot be empty.")
        person = await self._require_person(uow, person_id)
        existing = await uow.personnel.get_by_name(new_name)
        if existing is not None and existing.id != person.id:
            raise PersonnelServiceError(f"A person named '{new_name}' already exists.")
        await uow.personnel.update(person, name=new_name)
        return person

    async def remove_person(self, uow: UnitOfWorkProtocol, person_id: int) -> None:
        """Permanently remove a person and their duty history."""
        person = await self._require_person(uow, person_id)
        await uow.personnel.delete(person)
        logger.info("Removed personnel: %s (id=%s)", person.name, person_id)

    async def list_active(self, uow: UnitOfWorkProtocol) -> list[Personnel]:
        """List all active personnel."""
        return await uow.personnel.list_all(active_only=True)

    async def list_inactive(self, uow: UnitOfWorkProtocol) -> list[Personnel]:
        """List all inactive personnel."""
        all_people = await uow.personnel.list_all()
        return [p for p in all_people if not p.active]

    async def list_phone_holders(self, uow: UnitOfWorkProtocol) -> list[Personnel]:
        """List all active personnel who own a phone."""
        return await uow.personnel.list_phone_holders(active_only=True)

    async def find_or_none(self, uow: UnitOfWorkProtocol, name: str) -> Personnel | None:
        """Look up a person by exact name, case-insensitive."""
        return await uow.personnel.get_by_name(name)

    async def _require_person(self, uow: UnitOfWorkProtocol, person_id: int) -> Personnel:
        person = await uow.personnel.get_by_id(person_id)
        if person is None:
            raise PersonnelServiceError(f"Person with id={person_id} not found.")
        return person
