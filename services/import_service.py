"""Business logic for importing historical duty rosters.

Coordinates the parser, personnel matching, and persistence for the
``/add_duty`` workflow. Unknown names are never silently turned into new
personnel records; the caller (handler) must resolve each one explicitly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from database.unit_of_work import UnitOfWorkProtocol
from models.duty_assignment import DutyAssignment
from models.duty_category import DutyCategory
from models.personnel import Personnel
from models.week import Week
from services.parser_service import ParsedDuty

logger = logging.getLogger(__name__)


class ImportServiceError(Exception):
    """Raised for user-facing import failures."""


@dataclass(slots=True)
class ImportResolution:
    """The result of matching parsed names against existing personnel."""

    known: dict[str, Personnel] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)


class ImportService:
    """Resolves parsed duty names to personnel and persists imports."""

    async def resolve_names(self, uow: UnitOfWorkProtocol, parsed: ParsedDuty) -> ImportResolution:
        """Match every name referenced in ``parsed`` against known personnel."""
        resolution = ImportResolution()
        for name in sorted(parsed.all_names()):
            person = await uow.personnel.get_by_name(name)
            if person is not None:
                resolution.known[name] = person
            else:
                resolution.unknown.append(name)
        return resolution

    async def save_import(
        self,
        uow: UnitOfWorkProtocol,
        parsed: ParsedDuty,
        name_to_person: dict[str, Personnel],
    ) -> Week:
        """Persist a parsed roster, replacing any existing week with the same number.

        ``name_to_person`` must contain an entry for every name referenced by
        ``parsed`` (built from :meth:`resolve_names` plus any admin-resolved
        create/match/ignore decisions).
        """
        existing = await uow.weeks.get_by_number(parsed.week_number)
        if existing is not None:
            await uow.assignments.delete_for_week(existing.id)
            week = existing
        else:
            week = await uow.weeks.add(parsed.week_number, date.today(), published=True)

        assignments: list[DutyAssignment] = []
        for category, names in parsed.assignments.items():
            for name in names:
                person = name_to_person.get(name)
                if person is None:
                    continue  # Explicitly ignored by the admin during resolution.
                assignments.append(
                    DutyAssignment(week_id=week.id, category=category, meal=category.meal, person_id=person.id)
                )

        assigned_ids = {a.person_id for a in assignments}
        all_active = await uow.personnel.list_all(active_only=True)
        for person in all_active:
            if person.id not in assigned_ids:
                assignments.append(
                    DutyAssignment(
                        week_id=week.id,
                        category=DutyCategory.RESTING,
                        meal=DutyCategory.RESTING.meal,
                        person_id=person.id,
                    )
                )

        await uow.assignments.bulk_add(assignments)
        week.published = True
        logger.info("Imported historical week %s (%d assignments)", parsed.week_number, len(assignments))
        return week
