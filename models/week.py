"""Week ORM model."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.duty_assignment import DutyAssignment


class Week(Base):
    """A single week's duty roster."""

    __tablename__ = "weeks"

    id: Mapped[int] = mapped_column(primary_key=True)
    week_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    generated_date: Mapped[date] = mapped_column(Date, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignments: Mapped[list["DutyAssignment"]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Week(id={self.id!r}, week_number={self.week_number!r}, published={self.published!r})"
