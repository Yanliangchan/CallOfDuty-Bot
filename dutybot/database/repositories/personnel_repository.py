"""Repository for :class:`~models.personnel.Personnel` records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.personnel import Personnel


class PersonnelRepository:
    """Encapsulates all direct database access for personnel records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, name: str, *, has_phone: bool = False, active: bool = True, remarks: str | None = None
    ) -> Personnel:
        """Create and persist a new person."""
        person = Personnel(name=name, has_phone=has_phone, active=active, remarks=remarks)
        self._session.add(person)
        await self._session.flush()
        return person

    async def get_by_id(self, person_id: int) -> Personnel | None:
        """Fetch a person by primary key."""
        return await self._session.get(Personnel, person_id)

    async def get_by_name(self, name: str) -> Personnel | None:
        """Fetch a person by exact (case-insensitive) name match."""
        stmt = select(Personnel).where(Personnel.name.ilike(name))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_by_name(self, query: str) -> list[Personnel]:
        """Fuzzy-search personnel by a partial, case-insensitive name match."""
        stmt = select(Personnel).where(Personnel.name.ilike(f"%{query}%")).order_by(Personnel.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, *, active_only: bool = False) -> list[Personnel]:
        """List all personnel, optionally filtering to active members only."""
        stmt = select(Personnel).order_by(Personnel.name)
        if active_only:
            stmt = stmt.where(Personnel.active.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_phone_holders(self, *, active_only: bool = True) -> list[Personnel]:
        """List all personnel who own a phone."""
        stmt = select(Personnel).where(Personnel.has_phone.is_(True)).order_by(Personnel.name)
        if active_only:
            stmt = stmt.where(Personnel.active.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, person: Personnel, **fields: object) -> Personnel:
        """Update arbitrary fields on a person and persist the change."""
        for field_name, value in fields.items():
            setattr(person, field_name, value)
        await self._session.flush()
        return person

    async def delete(self, person: Personnel) -> None:
        """Permanently delete a person and their duty history."""
        await self._session.delete(person)
        await self._session.flush()
