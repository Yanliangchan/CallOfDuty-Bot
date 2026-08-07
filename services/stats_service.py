"""Business logic for computing personnel duty statistics."""

from __future__ import annotations

from dataclasses import dataclass

from database.unit_of_work import UnitOfWorkProtocol
from models.duty_category import DutyCategory
from models.personnel import Personnel


@dataclass(slots=True)
class PersonStats:
    """Aggregated duty statistics for a single person."""

    person: Personnel
    category_counts: dict[DutyCategory, int]
    last_assigned_week: int | None


class StatsService:
    """Computes duty statistics for personnel."""

    async def stats_for_person(self, uow: UnitOfWorkProtocol, person: Personnel) -> PersonStats:
        """Compute statistics for a single person."""
        counts = await uow.assignments.count_by_category_for_person(person.id)
        last_week = await uow.assignments.last_assigned_week_number(person.id)
        return PersonStats(person=person, category_counts=counts, last_assigned_week=last_week)

    async def stats_for_all(self, uow: UnitOfWorkProtocol, *, active_only: bool = False) -> list[PersonStats]:
        """Compute statistics for every person, ordered by name."""
        people = await uow.personnel.list_all(active_only=active_only)
        return [await self.stats_for_person(uow, person) for person in people]


def render_person_stats(stats: PersonStats) -> str:
    """Render a single person's statistics block for Telegram display."""
    lines = [stats.person.name, ""]
    labels: dict[DutyCategory, str] = {
        DutyCategory.BREAKFAST_TRASH: "Breakfast Trash",
        DutyCategory.LUNCH_TRASH: "Lunch Trash",
        DutyCategory.DINNER_TRASH: "Dinner Trash",
        DutyCategory.LUNCH_RATION: "Lunch Ration",
        DutyCategory.DINNER_RATION: "Dinner Ration",
        DutyCategory.SAFETY_STORE: "Safety Store",
        DutyCategory.KEY_DUTY: "Key Duty",
        DutyCategory.RESTING: "Resting",
    }
    for category, label in labels.items():
        count = stats.category_counts.get(category, 0)
        lines.append(f"{label}: {count}")
    lines.append("")
    if stats.last_assigned_week is not None:
        lines.append("Last Week Assigned:")
        lines.append(f"Week {stats.last_assigned_week}")
    else:
        lines.append("Last Week Assigned: None")
    return "\n".join(lines)


def render_all_stats(all_stats: list[PersonStats]) -> str:
    """Render statistics for every person, separated by blank lines."""
    blocks = [render_person_stats(stats) for stats in all_stats]
    return "\n\n".join(blocks) if blocks else "No personnel records found."
