"""Fair duty-scheduling algorithm.

The algorithm assigns personnel to each duty category using weighted random
selection so that, over time, duties are distributed evenly. Two signals
drive the weighting for a given category:

* How many times a person has already performed that specific category
  (fewer past occurrences -> higher weight).
* How long ago the person was last assigned *any* duty (longer since their
  last assignment -> higher weight), so the same people are not picked
  every week.

Categories that require a phone holder are guaranteed at least one assignee
with ``has_phone=True`` by swapping in the best-weighted available phone
holder if none was picked by chance.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from database.unit_of_work import UnitOfWorkProtocol
from models.duty_category import ASSIGNABLE_CATEGORIES, DutyCategory
from models.personnel import Personnel

logger = logging.getLogger(__name__)

#: Weight assigned to a person who has never been assigned this category.
_NEVER_ASSIGNED_CATEGORY_BONUS = 3.0

#: Weight assigned to a person who has never had any duty at all.
_NEVER_ASSIGNED_OVERALL_BONUS = 6.0

#: Minimum weight floor so nobody has literally zero chance of selection.
_MIN_WEIGHT = 0.1


@dataclass(slots=True)
class PersonScheduleContext:
    """Historical scheduling data for one person, used to compute weights."""

    person: Personnel
    category_counts: dict[DutyCategory, int]
    last_assigned_week: int | None


class SchedulingService:
    """Generates a fair set of duty assignments for a new week."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    async def build_contexts(
        self, uow: UnitOfWorkProtocol, people: list[Personnel]
    ) -> list[PersonScheduleContext]:
        """Load historical assignment data needed to weight each candidate."""
        contexts: list[PersonScheduleContext] = []
        for person in people:
            counts = await uow.assignments.count_by_category_for_person(person.id)
            last_week = await uow.assignments.last_assigned_week_number(person.id)
            contexts.append(PersonScheduleContext(person=person, category_counts=counts, last_assigned_week=last_week))
        return contexts

    def _weight_for(
        self, ctx: PersonScheduleContext, category: DutyCategory, current_week_number: int
    ) -> float:
        category_count = ctx.category_counts.get(category, 0)
        category_weight = _NEVER_ASSIGNED_CATEGORY_BONUS if category_count == 0 else 1.0 / category_count

        if ctx.last_assigned_week is None:
            recency_weight = _NEVER_ASSIGNED_OVERALL_BONUS
        else:
            weeks_since = max(current_week_number - ctx.last_assigned_week, 0)
            recency_weight = 1.0 + weeks_since

        weight = category_weight * recency_weight
        return max(weight, _MIN_WEIGHT)

    def _weighted_sample(
        self,
        candidates: list[PersonScheduleContext],
        weights: list[float],
        count: int,
    ) -> list[PersonScheduleContext]:
        """Sample ``count`` distinct contexts from ``candidates`` without replacement."""
        pool = list(zip(candidates, weights))
        chosen: list[PersonScheduleContext] = []
        for _ in range(min(count, len(pool))):
            total = sum(w for _, w in pool)
            pick_point = self._rng.uniform(0, total)
            running = 0.0
            for index, (ctx, weight) in enumerate(pool):
                running += weight
                if running >= pick_point:
                    chosen.append(ctx)
                    pool.pop(index)
                    break
        return chosen

    def generate_assignments(
        self,
        contexts: list[PersonScheduleContext],
        week_number: int,
    ) -> dict[DutyCategory, list[Personnel]]:
        """Assign personnel to every category, returning the resulting roster.

        Personnel already used this week are excluded from later categories,
        preventing duplicate duties within the same week. Whoever remains
        unassigned after all other categories are filled is placed on
        ``RESTING``.
        """
        remaining = list(contexts)
        result: dict[DutyCategory, list[Personnel]] = {}

        for category in ASSIGNABLE_CATEGORIES:
            group_size = category.group_size
            if group_size == 0 or not remaining:
                result[category] = []
                continue

            weights = [self._weight_for(ctx, category, week_number) for ctx in remaining]
            selected = self._weighted_sample(remaining, weights, group_size)

            if category.requires_phone_holder and selected and not any(
                ctx.person.has_phone for ctx in selected
            ):
                selected = self._ensure_phone_holder(selected, remaining, category, week_number)

            for ctx in selected:
                remaining.remove(ctx)

            result[category] = [ctx.person for ctx in selected]

        result[DutyCategory.RESTING] = [ctx.person for ctx in remaining]
        return result

    def _ensure_phone_holder(
        self,
        selected: list[PersonScheduleContext],
        remaining: list[PersonScheduleContext],
        category: DutyCategory,
        week_number: int,
    ) -> list[PersonScheduleContext]:
        """Swap the weakest non-phone-holder pick for the best available phone holder."""
        available_phone_holders = [
            ctx
            for ctx in remaining
            if ctx.person.has_phone and ctx not in selected
        ]
        if not available_phone_holders:
            logger.warning(
                "No available phone holder to satisfy category=%s in week=%s", category, week_number
            )
            return selected

        best_phone_holder = max(
            available_phone_holders, key=lambda ctx: self._weight_for(ctx, category, week_number)
        )
        worst_index = min(
            range(len(selected)),
            key=lambda i: self._weight_for(selected[i], category, week_number),
        )
        selected[worst_index] = best_phone_holder
        return selected
