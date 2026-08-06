"""Repository for :class:`~models.duty_assignment.DutyAssignment` records."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.duty_assignment import DutyAssignment
from models.duty_category import DutyCategory
from models.week import Week


class DutyAssignmentRepository:
    """Encapsulates all direct database access for duty assignments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, week_id: int, category: DutyCategory, person_id: int) -> DutyAssignment:
        """Create and persist a single duty assignment."""
        assignment = DutyAssignment(
            week_id=week_id, category=category, meal=category.meal, person_id=person_id
        )
        self._session.add(assignment)
        await self._session.flush()
        return assignment

    async def bulk_add(self, assignments: list[DutyAssignment]) -> None:
        """Persist many assignments in a single flush."""
        self._session.add_all(assignments)
        await self._session.flush()

    async def list_for_week(self, week_id: int) -> list[DutyAssignment]:
        """List all assignments for a given week, with person eager-loaded."""
        stmt = (
            select(DutyAssignment)
            .where(DutyAssignment.week_id == week_id)
            .options(selectinload(DutyAssignment.person))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_person(self, person_id: int) -> list[DutyAssignment]:
        """List every historical assignment for a person, newest week first."""
        stmt = (
            select(DutyAssignment)
            .join(Week, DutyAssignment.week_id == Week.id)
            .where(DutyAssignment.person_id == person_id)
            .options(selectinload(DutyAssignment.week))
            .order_by(Week.week_number.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_category_for_person(self, person_id: int) -> dict[DutyCategory, int]:
        """Count how many times a person has performed each duty category."""
        stmt = (
            select(DutyAssignment.category, func.count(DutyAssignment.id))
            .where(DutyAssignment.person_id == person_id)
            .group_by(DutyAssignment.category)
        )
        result = await self._session.execute(stmt)
        return {category: count for category, count in result.all()}

    async def last_assigned_week_number(self, person_id: int) -> int | None:
        """Return the most recent week number a person had any assignment."""
        stmt = (
            select(func.max(Week.week_number))
            .join(DutyAssignment, DutyAssignment.week_id == Week.id)
            .where(DutyAssignment.person_id == person_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def last_assigned_week_number_for_category(
        self, person_id: int, category: DutyCategory
    ) -> int | None:
        """Return the most recent week number a person performed ``category``."""
        stmt = (
            select(func.max(Week.week_number))
            .join(DutyAssignment, DutyAssignment.week_id == Week.id)
            .where(DutyAssignment.person_id == person_id, DutyAssignment.category == category)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_for_week(self, week_id: int) -> None:
        """Remove all assignments belonging to a week (used before regenerating)."""
        stmt = select(DutyAssignment).where(DutyAssignment.week_id == week_id)
        result = await self._session.execute(stmt)
        for assignment in result.scalars().all():
            await self._session.delete(assignment)
        await self._session.flush()
