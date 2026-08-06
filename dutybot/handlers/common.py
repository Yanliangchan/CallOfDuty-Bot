"""Shared helpers for Telegram handlers."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.formatting import render_week_selection_keyboard_label


def build_week_picker(week_numbers: list[int], *, prefix: str, columns: int = 4) -> InlineKeyboardMarkup:
    """Build an inline keyboard of week buttons, most recent first."""
    buttons = [
        InlineKeyboardButton(render_week_selection_keyboard_label(number), callback_data=f"{prefix}:{number}")
        for number in sorted(week_numbers, reverse=True)
    ]
    rows = [buttons[i : i + columns] for i in range(0, len(buttons), columns)]
    return InlineKeyboardMarkup(rows)


PERSONNEL_MENU_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Add Person", callback_data="pers:add")],
        [InlineKeyboardButton("Edit Person", callback_data="pers:edit_menu")],
        [InlineKeyboardButton("Remove Person", callback_data="pers:remove_menu")],
        [InlineKeyboardButton("Phone Holders", callback_data="pers:phone_menu")],
        [InlineKeyboardButton("Inactive Personnel", callback_data="pers:inactive_list")],
        [InlineKeyboardButton("Statistics", callback_data="pers:stats")],
    ]
)
