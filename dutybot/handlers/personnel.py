"""Handlers for /personnel: interactive personnel management."""

from __future__ import annotations

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database.unit_of_work import UnitOfWork
from handlers.common import PERSONNEL_MENU_KEYBOARD
from models.personnel import Personnel
from services.personnel_service import PersonnelService, PersonnelServiceError
from utils.decorators import admin_only, log_errors

_personnel_service = PersonnelService()


def _person_line(person: Personnel) -> str:
    phone = "📱" if person.has_phone else "  "
    status = "" if person.active else " (inactive)"
    return f"{phone} {person.name}{status}"


@log_errors
@admin_only
async def personnel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the personnel management menu."""
    message = update.effective_message
    if message is None:
        return
    await message.reply_text("Personnel Manager", reply_markup=PERSONNEL_MENU_KEYBOARD)


@log_errors
@admin_only
async def personnel_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route personnel menu button presses."""
    query = update.callback_query
    if query is None or query.data is None or context.chat_data is None:
        return
    await query.answer()
    action = query.data.split(":", 1)[1]

    if action == "menu":
        await query.edit_message_text("Personnel Manager", reply_markup=PERSONNEL_MENU_KEYBOARD)
    elif action == "add":
        await query.edit_message_text("Send the new person's name as a message.")
        context.chat_data["awaiting"] = "add_name"
    elif action == "stats":
        await _show_statistics(query, context)
    elif action == "inactive_list":
        await _show_inactive(query, context)
    elif action == "phone_menu":
        await _show_phone_menu(query, context)
    elif action.startswith("phone_toggle:"):
        person_id = int(action.split(":")[1])
        async with UnitOfWork() as uow:
            await _personnel_service.toggle_phone(uow, person_id)
        await _show_phone_menu(query, context)
    elif action == "edit_menu":
        await _show_select_list(query, context, purpose="edit")
    elif action == "remove_menu":
        await _show_select_list(query, context, purpose="remove")
    elif action.startswith("select_edit:"):
        person_id = int(action.split(":")[1])
        context.chat_data["edit_person_id"] = person_id
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Toggle Phone", callback_data=f"pers:edit_toggle_phone:{person_id}")],
                [InlineKeyboardButton("Toggle Active", callback_data=f"pers:edit_toggle_active:{person_id}")],
                [InlineKeyboardButton("Rename", callback_data=f"pers:edit_rename:{person_id}")],
                [InlineKeyboardButton("Edit Remarks", callback_data=f"pers:edit_remarks:{person_id}")],
                [InlineKeyboardButton("Back", callback_data="pers:menu")],
            ]
        )
        await query.edit_message_text("What would you like to edit?", reply_markup=keyboard)
    elif action.startswith("edit_toggle_phone:"):
        person_id = int(action.split(":")[1])
        async with UnitOfWork() as uow:
            person = await _personnel_service.toggle_phone(uow, person_id)
        await query.edit_message_text(f"Updated {person.name}: phone={person.has_phone}")
    elif action.startswith("edit_toggle_active:"):
        person_id = int(action.split(":")[1])
        async with UnitOfWork() as uow:
            existing = await uow.personnel.get_by_id(person_id)
            new_active = not existing.active if existing is not None else True
            person = await _personnel_service.set_active(uow, person_id, new_active)
        await query.edit_message_text(f"Updated {person.name}: active={person.active}")
    elif action.startswith("edit_rename:"):
        person_id = int(action.split(":")[1])
        context.chat_data["awaiting"] = "rename"
        context.chat_data["edit_person_id"] = person_id
        await query.edit_message_text("Send the new name as a message.")
    elif action.startswith("edit_remarks:"):
        person_id = int(action.split(":")[1])
        context.chat_data["awaiting"] = "remarks"
        context.chat_data["edit_person_id"] = person_id
        await query.edit_message_text("Send the new remarks as a message.")
    elif action.startswith("select_remove:"):
        person_id = int(action.split(":")[1])
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Confirm Remove", callback_data=f"pers:confirm_remove:{person_id}")],
                [InlineKeyboardButton("Cancel", callback_data="pers:menu")],
            ]
        )
        await query.edit_message_text("Are you sure? This deletes their full duty history.", reply_markup=keyboard)
    elif action.startswith("confirm_remove:"):
        person_id = int(action.split(":")[1])
        async with UnitOfWork() as uow:
            await _personnel_service.remove_person(uow, person_id)
        await query.edit_message_text("Person removed.", reply_markup=PERSONNEL_MENU_KEYBOARD)


async def _show_statistics(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    from services.stats_service import StatsService, render_all_stats

    async with UnitOfWork() as uow:
        all_stats = await StatsService().stats_for_all(uow)
    text = render_all_stats(all_stats)
    await query.edit_message_text(text[:4000])


async def _show_inactive(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with UnitOfWork() as uow:
        inactive = await _personnel_service.list_inactive(uow)
    if not inactive:
        await query.edit_message_text("No inactive personnel.", reply_markup=PERSONNEL_MENU_KEYBOARD)
        return
    text = "Inactive Personnel:\n\n" + "\n".join(_person_line(p) for p in inactive)
    await query.edit_message_text(text, reply_markup=PERSONNEL_MENU_KEYBOARD)


async def _show_phone_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with UnitOfWork() as uow:
        people = await _personnel_service.list_active(uow)
    buttons = [
        [
            InlineKeyboardButton(
                f"{'✅' if p.has_phone else '❌'} {p.name}", callback_data=f"pers:phone_toggle:{p.id}"
            )
        ]
        for p in people
    ]
    buttons.append([InlineKeyboardButton("Back", callback_data="pers:menu")])
    await query.edit_message_text("Tap a name to toggle phone ownership:", reply_markup=InlineKeyboardMarkup(buttons))


async def _show_select_list(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, *, purpose: str) -> None:
    async with UnitOfWork() as uow:
        people = await _personnel_service.list_active(uow)
    action_prefix = "select_edit" if purpose == "edit" else "select_remove"
    buttons = [[InlineKeyboardButton(p.name, callback_data=f"pers:{action_prefix}:{p.id}")] for p in people]
    buttons.append([InlineKeyboardButton("Back", callback_data="pers:menu")])
    verb = "edit" if purpose == "edit" else "remove"
    await query.edit_message_text(f"Select a person to {verb}:", reply_markup=InlineKeyboardMarkup(buttons))


async def personnel_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-text replies used by the personnel manager (name/remarks input)."""
    message = update.effective_message
    if message is None or message.text is None or context.chat_data is None:
        return
    awaiting = context.chat_data.get("awaiting")
    if awaiting not in ("add_name", "rename", "remarks"):
        return

    text = message.text.strip()
    try:
        if awaiting == "add_name":
            async with UnitOfWork() as uow:
                await _personnel_service.add_person(uow, text)
            await message.reply_text(f"Added {text}.", reply_markup=PERSONNEL_MENU_KEYBOARD)
        elif awaiting == "rename":
            person_id = context.chat_data["edit_person_id"]
            async with UnitOfWork() as uow:
                person = await _personnel_service.rename(uow, person_id, text)
            await message.reply_text(f"Renamed to {person.name}.", reply_markup=PERSONNEL_MENU_KEYBOARD)
        elif awaiting == "remarks":
            person_id = context.chat_data["edit_person_id"]
            async with UnitOfWork() as uow:
                person = await _personnel_service.update_remarks(uow, person_id, text)
            await message.reply_text(f"Updated remarks for {person.name}.", reply_markup=PERSONNEL_MENU_KEYBOARD)
    except PersonnelServiceError as exc:
        await message.reply_text(str(exc))
    finally:
        context.chat_data.pop("awaiting", None)
        context.chat_data.pop("edit_person_id", None)
