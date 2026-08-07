"""Unit-of-work helper bundling a session with its repositories.

Services depend on :class:`UnitOfWork` rather than on SQLAlchemy directly,
keeping persistence concerns out of business logic.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.duty_assignment_repository import DutyAssignmentRepository
from database.repositories.personnel_repository import PersonnelRepository
from database.repositories.week_repository import WeekRepository
from database.session import get_sessionmaker


class UnitOfWorkProtocol(Protocol):
    """Structural interface services depend on instead of the concrete class.

    This lets tests substitute a lightweight fake (e.g. one backed by an
    in-memory SQLite session) without needing to inherit from
    :class:`UnitOfWork` itself.
    """

    personnel: PersonnelRepository
    weeks: WeekRepository
    assignments: DutyAssignmentRepository


class UnitOfWork:
    """Async context manager providing a session and its repositories.

    On successful exit the transaction is committed; on any exception it is
    rolled back and the exception re-raised.
    """

    def __init__(self) -> None:
        self._sessionmaker = get_sessionmaker()
        self.session: AsyncSession | None = None
        self.personnel: PersonnelRepository
        self.weeks: WeekRepository
        self.assignments: DutyAssignmentRepository

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._sessionmaker()
        self.personnel = PersonnelRepository(self.session)
        self.weeks = WeekRepository(self.session)
        self.assignments = DutyAssignmentRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self.session is not None
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
