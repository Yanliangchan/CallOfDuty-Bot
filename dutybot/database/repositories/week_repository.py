"""Repository for :class:`~models.week.Week` records."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.duty_assignment import DutyAssignment
from models.week import Week


class WeekRepository:
    """Encapsulates all direct database access for weekly rosters."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, week_number: int, generated_date: date, *, published: bool = False) -> Week:
        """Create and persist a new week."""
        week = Week(week_number=week_number, generated_date=generated_date, published=published)
        self._session.add(week)
        await self._session.flush()
        return week

    async def get_by_id(self, week_id: int, *, with_assignments: bool = False) -> Week | None:
        """Fetch a week by primary key, optionally eager-loading assignments."""
        stmt = select(Week).where(Week.id == week_id)
        if with_assignments:
            stmt = stmt.options(
                selectinload(Week.assignments).selectinload(DutyAssignment.person)
            )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_number(self, week_number: int, *, with_assignments: bool = False) -> Week | None:
        """Fetch a week by its week number, optionally eager-loading assignments."""
        stmt = select(Week).where(Week.week_number == week_number)
        if with_assignments:
            stmt = stmt.options(
                selectinload(Week.assignments).selectinload(DutyAssignment.person)
            )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest(self) -> Week | None:
        """Fetch the most recently numbered week, published or not."""
        stmt = select(Week).order_by(Week.week_number.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_published(self) -> Week | None:
        """Fetch the most recent published week."""
        stmt = (
            select(Week)
            .where(Week.published.is_(True))
            .order_by(Week.week_number.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Week]:
        """List every week ordered by week number ascending."""
        stmt = select(Week).order_by(Week.week_number)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def next_week_number(self) -> int:
        """Compute the next sequential week number."""
        stmt = select(func.max(Week.week_number))
        result = await self._session.execute(stmt)
        current_max = result.scalar_one_or_none()
        return (current_max or 0) + 1

    async def mark_published(self, week: Week) -> Week:
        """Mark a week as published."""
        week.published = True
        await self._session.flush()
        return week

    async def delete(self, week: Week) -> None:
        """Permanently delete a week and its assignments."""
        await self._session.delete(week)
        await self._session.flush()
