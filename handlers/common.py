"""Shared helpers for Telegram handlers."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from utils.formatting import render_week_selection_keyboard_label

#: Labels for the persistent main-menu reply keyboard shown after /start.
#: Kept as a flat mapping so the text router can dispatch a tapped button
#: straight to its command handler.
MAIN_MENU_LABELS: dict[str, str] = {
    "see_duty": "📅 See Duty",
    "see_past": "📜 See Past",
    "stats": "📊 Stats",
    "help": "❓ Help",
    "personnel": "👥 Personnel",
    "generate": "🎲 Generate",
    "publish": "📢 Publish",
    "add_duty": "📥 Add Duty",
}


def build_main_menu(*, is_admin: bool) -> ReplyKeyboardMarkup:
    """Build the persistent bottom-of-screen menu, with extra rows for admins."""
    rows = [
        [MAIN_MENU_LABELS["see_duty"], MAIN_MENU_LABELS["see_past"]],
        [MAIN_MENU_LABELS["stats"], MAIN_MENU_LABELS["help"]],
    ]
    if is_admin:
        rows.append([MAIN_MENU_LABELS["personnel"], MAIN_MENU_LABELS["add_duty"]])
        rows.append([MAIN_MENU_LABELS["generate"], MAIN_MENU_LABELS["publish"]])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


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
