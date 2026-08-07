"""Enumerations describing duty categories and meal slots.

Keeping these as plain ``str`` enums (rather than PostgreSQL native enums)
makes it trivial to add new duty types in the future without an Alembic
migration to alter a database-level enum type.
"""

from __future__ import annotations

import enum


class Meal(str, enum.Enum):
    """A meal slot within a duty day, or ``NONE`` for day-level duties."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    NONE = "none"


class DutyCategory(str, enum.Enum):
    """A specific type of duty that can be assigned to personnel.

    New duty types can be appended here without touching the database
    schema, since ``category`` is stored as a plain string column.
    """

    BREAKFAST_TRASH = "breakfast_trash"
    LUNCH_TRASH = "lunch_trash"
    LUNCH_RATION = "lunch_ration"
    DINNER_TRASH = "dinner_trash"
    DINNER_RATION = "dinner_ration"
    SAFETY_STORE = "safety_store"
    KEY_DUTY = "key_duty"
    RESTING = "resting"

    @property
    def display_name(self) -> str:
        """Human readable label used when rendering duty messages."""
        return _DISPLAY_NAMES[self]

    @property
    def meal(self) -> Meal:
        """The meal slot this category belongs to, if any."""
        return _CATEGORY_MEAL[self]

    @property
    def requires_phone_holder(self) -> bool:
        """Whether at least one assignee must own a phone."""
        return self in _PHONE_REQUIRED

    @property
    def group_size(self) -> int:
        """Number of people normally assigned to this category."""
        return _GROUP_SIZE[self]


_DISPLAY_NAMES: dict[DutyCategory, str] = {
    DutyCategory.BREAKFAST_TRASH: "Throw Trash",
    DutyCategory.LUNCH_TRASH: "Throw Trash",
    DutyCategory.LUNCH_RATION: "Get / Return Ration",
    DutyCategory.DINNER_TRASH: "Throw Trash",
    DutyCategory.DINNER_RATION: "Get / Return Ration",
    DutyCategory.SAFETY_STORE: "Safety Stores",
    DutyCategory.KEY_DUTY: "Key Duty",
    DutyCategory.RESTING: "Resting",
}

_CATEGORY_MEAL: dict[DutyCategory, Meal] = {
    DutyCategory.BREAKFAST_TRASH: Meal.BREAKFAST,
    DutyCategory.LUNCH_TRASH: Meal.LUNCH,
    DutyCategory.LUNCH_RATION: Meal.LUNCH,
    DutyCategory.DINNER_TRASH: Meal.DINNER,
    DutyCategory.DINNER_RATION: Meal.DINNER,
    DutyCategory.SAFETY_STORE: Meal.NONE,
    DutyCategory.KEY_DUTY: Meal.NONE,
    DutyCategory.RESTING: Meal.NONE,
}

_PHONE_REQUIRED: frozenset[DutyCategory] = frozenset(
    {
        DutyCategory.BREAKFAST_TRASH,
        DutyCategory.LUNCH_TRASH,
        DutyCategory.LUNCH_RATION,
        DutyCategory.DINNER_TRASH,
        DutyCategory.DINNER_RATION,
        DutyCategory.KEY_DUTY,
    }
)

_GROUP_SIZE: dict[DutyCategory, int] = {
    DutyCategory.BREAKFAST_TRASH: 2,
    DutyCategory.LUNCH_TRASH: 2,
    DutyCategory.LUNCH_RATION: 2,
    DutyCategory.DINNER_TRASH: 2,
    DutyCategory.DINNER_RATION: 2,
    DutyCategory.SAFETY_STORE: 3,
    DutyCategory.KEY_DUTY: 2,
    DutyCategory.RESTING: 0,
}

#: Categories in the order they should appear when rendering a duty roster.
CATEGORY_DISPLAY_ORDER: tuple[DutyCategory, ...] = (
    DutyCategory.BREAKFAST_TRASH,
    DutyCategory.LUNCH_TRASH,
    DutyCategory.LUNCH_RATION,
    DutyCategory.DINNER_TRASH,
    DutyCategory.DINNER_RATION,
    DutyCategory.SAFETY_STORE,
    DutyCategory.KEY_DUTY,
    DutyCategory.RESTING,
)

#: Categories that are assigned by the fair-scheduling algorithm (excludes
#: RESTING, which is derived from whoever is left over).
ASSIGNABLE_CATEGORIES: tuple[DutyCategory, ...] = tuple(
    category for category in CATEGORY_DISPLAY_ORDER if category != DutyCategory.RESTING
)
