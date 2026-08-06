"""Shared pytest fixtures for DutyBot's test suite.

Sets required environment variables before any application module is
imported (``config.py`` validates them at import time), and provides an
in-memory SQLite session for repository/service-level tests.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_IDS", "1,2")
os.environ.setdefault("GROUP_CHAT_ID", "-100123456")
os.environ.setdefault("GROUP_TOPIC_ID", "")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.repositories.duty_assignment_repository import DutyAssignmentRepository
from database.repositories.personnel_repository import PersonnelRepository
from database.repositories.week_repository import WeekRepository
from models import Base


class FakeUnitOfWork:
    """Minimal stand-in for :class:`database.unit_of_work.UnitOfWork` in tests.

    Services only depend on the ``personnel``/``weeks``/``assignments``
    attributes, so tests can use this lightweight wrapper around a shared
    in-memory SQLite session instead of the real Postgres-backed engine.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.personnel = PersonnelRepository(session)
        self.weeks = WeekRepository(session)
        self.assignments = DutyAssignmentRepository(session)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` backed by a fresh in-memory SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as sess:
        yield sess

    await engine.dispose()


@pytest_asyncio.fixture
async def uow(session: AsyncSession) -> FakeUnitOfWork:
    """Yield a :class:`FakeUnitOfWork` bound to the test session."""
    return FakeUnitOfWork(session)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
