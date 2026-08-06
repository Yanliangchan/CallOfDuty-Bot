"""Tests for the fair duty-scheduling algorithm."""

from __future__ import annotations

import random

from models.duty_category import ASSIGNABLE_CATEGORIES, DutyCategory
from models.personnel import Personnel
from services.scheduling_service import PersonScheduleContext, SchedulingService


def _make_person(person_id: int, name: str, has_phone: bool) -> Personnel:
    person = Personnel(name=name, has_phone=has_phone, active=True)
    person.id = person_id
    return person


def _fresh_context(person: Personnel) -> PersonScheduleContext:
    return PersonScheduleContext(person=person, category_counts={}, last_assigned_week=None)


def test_generate_assignments_fills_every_category_group_size() -> None:
    people = [_make_person(i, f"Person{i}", has_phone=(i % 2 == 0)) for i in range(1, 16)]
    contexts = [_fresh_context(p) for p in people]

    service = SchedulingService(rng=random.Random(42))
    roster = service.generate_assignments(contexts, week_number=1)

    for category in ASSIGNABLE_CATEGORIES:
        assert len(roster[category]) == min(category.group_size, len(people))


def test_no_duplicate_person_within_same_week() -> None:
    people = [_make_person(i, f"Person{i}", has_phone=(i % 3 == 0)) for i in range(1, 20)]
    contexts = [_fresh_context(p) for p in people]

    service = SchedulingService(rng=random.Random(7))
    roster = service.generate_assignments(contexts, week_number=1)

    seen_ids: set[int] = set()
    for assignees in roster.values():
        for person in assignees:
            assert person.id not in seen_ids
            seen_ids.add(person.id)


def test_phone_holder_requirement_is_satisfied_when_possible() -> None:
    # Six categories require a phone holder; use a generous surplus of phone
    # holders so a single unlucky draw can't exhaust the supply early.
    people = [_make_person(i, f"PhoneHolder{i}", has_phone=True) for i in range(1, 16)]
    people += [_make_person(i, f"Extra{i}", has_phone=False) for i in range(16, 25)]
    contexts = [_fresh_context(p) for p in people]

    service = SchedulingService(rng=random.Random(1))
    roster = service.generate_assignments(contexts, week_number=1)

    for category in ASSIGNABLE_CATEGORIES:
        if category.requires_phone_holder and roster[category]:
            assert any(p.has_phone for p in roster[category])


def test_remaining_personnel_are_assigned_to_resting() -> None:
    people = [_make_person(i, f"Person{i}", has_phone=True) for i in range(1, 30)]
    contexts = [_fresh_context(p) for p in people]

    service = SchedulingService(rng=random.Random(3))
    roster = service.generate_assignments(contexts, week_number=1)

    assigned_count = sum(len(v) for cat, v in roster.items() if cat != DutyCategory.RESTING)
    resting_count = len(roster[DutyCategory.RESTING])
    assert assigned_count + resting_count == len(people)


def test_never_assigned_category_is_weighted_more_heavily() -> None:
    heavy_user = _make_person(1, "AlreadyDidTrashLots", has_phone=True)
    fresh_user = _make_person(2, "NeverDidTrash", has_phone=True)

    heavy_ctx = PersonScheduleContext(
        person=heavy_user, category_counts={DutyCategory.BREAKFAST_TRASH: 20}, last_assigned_week=10
    )
    fresh_ctx = PersonScheduleContext(person=fresh_user, category_counts={}, last_assigned_week=None)

    service = SchedulingService()
    heavy_weight = service._weight_for(heavy_ctx, DutyCategory.BREAKFAST_TRASH, current_week_number=11)
    fresh_weight = service._weight_for(fresh_ctx, DutyCategory.BREAKFAST_TRASH, current_week_number=11)

    assert fresh_weight > heavy_weight
