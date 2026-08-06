"""DutyAssignment ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.duty_category import DutyCategory, Meal

if TYPE_CHECKING:
    from models.personnel import Personnel
    from models.week import Week


class DutyAssignment(Base):
    """A single person's assignment to a duty category within a week."""

    __tablename__ = "duty_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[DutyCategory] = mapped_column(
        Enum(DutyCategory, name="duty_category", native_enum=False, length=32), nullable=False
    )
    meal: Mapped[Meal] = mapped_column(
        Enum(Meal, name="duty_meal", native_enum=False, length=16), nullable=False, default=Meal.NONE
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False, index=True
    )

    week: Mapped["Week"] = relationship(back_populates="assignments")
    person: Mapped["Personnel"] = relationship(back_populates="assignments")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"DutyAssignment(week_id={self.week_id!r}, category={self.category!r}, "
            f"person_id={self.person_id!r})"
        )
