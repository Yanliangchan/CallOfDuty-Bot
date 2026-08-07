"""Rendering of duty rosters and statistics into Telegram message text."""

from __future__ import annotations

from collections import defaultdict

from models.duty_assignment import DutyAssignment
from models.duty_category import DutyCategory
from models.personnel import Personnel

_MEAL_SECTIONS: tuple[tuple[str, tuple[DutyCategory, ...]], ...] = (
    ("Breakfast", (DutyCategory.BREAKFAST_TRASH,)),
    ("Lunch", (DutyCategory.LUNCH_TRASH, DutyCategory.LUNCH_RATION)),
    ("Dinner", (DutyCategory.DINNER_TRASH, DutyCategory.DINNER_RATION)),
)

_STANDALONE_SECTIONS: tuple[DutyCategory, ...] = (
    DutyCategory.SAFETY_STORE,
    DutyCategory.KEY_DUTY,
    DutyCategory.RESTING,
)


def _person_label(person: Personnel) -> str:
    return f"{person.name} 📱" if person.has_phone else person.name


def _group_by_category(assignments: list[DutyAssignment]) -> dict[DutyCategory, list[Personnel]]:
    by_category: dict[DutyCategory, list[Personnel]] = defaultdict(list)
    for assignment in assignments:
        by_category[assignment.category].append(assignment.person)
    for people in by_category.values():
        people.sort(key=lambda p: p.name)
    return by_category


def render_week_roster(week_number: int, assignments: list[DutyAssignment]) -> str:
    """Render a full duty roster message for one week, grouped by meal/category."""
    by_category = _group_by_category(assignments)
    lines: list[str] = [f"Week {week_number} Duty", ""]

    for meal_title, categories in _MEAL_SECTIONS:
        lines.append(meal_title)
        lines.append("")
        any_ration_category = any(c in (DutyCategory.LUNCH_RATION, DutyCategory.DINNER_RATION) for c in categories)
        has_ration_assignment = False
        for category in categories:
            people = by_category.get(category, [])
            if category in (DutyCategory.LUNCH_RATION, DutyCategory.DINNER_RATION) and people:
                has_ration_assignment = True
            if not people:
                continue
            lines.append(category.display_name)
            for person in people:
                lines.append(f"• {_person_label(person)}")
            lines.append("")
        if any_ration_category and not has_ration_assignment:
            lines.append("No ration")
            lines.append("")

    for category in _STANDALONE_SECTIONS:
        people = by_category.get(category, [])
        lines.append(category.display_name)
        if people:
            for person in people:
                lines.append(f"• {_person_label(person)}")
        else:
            lines.append("• None")
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def render_week_selection_keyboard_label(week_number: int) -> str:
    """Return the button label used for a week in the /see_past picker."""
    return f"Week {week_number}"
