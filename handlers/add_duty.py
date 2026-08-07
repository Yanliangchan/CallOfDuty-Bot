"""Handlers for /add_duty: importing historical duty rosters by pasting text."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from database.unit_of_work import UnitOfWork
from models.duty_category import CATEGORY_DISPLAY_ORDER
from models.personnel import Personnel
from services.import_service import ImportService, ImportServiceError
from services.parser_service import DutyParseError, ParsedDuty, parse_duty_text
from services.personnel_service import PersonnelService
from utils.decorators import admin_only, log_errors

ReplyFunc = Callable[..., Awaitable[Message]]

logger = logging.getLogger(__name__)

_import_service = ImportService()
_personnel_service = PersonnelService()


def _render_preview(parsed: ParsedDuty) -> str:
    lines = [f"Week {parsed.week_number}", ""]
    for category in CATEGORY_DISPLAY_ORDER:
        names = parsed.names_for(category)
        if not names:
            continue
        lines.append(category.display_name)
        for name in names:
            lines.append(f"• {name}")
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


@log_errors
@admin_only
async def add_duty_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the import workflow by asking the admin to paste a duty list."""
    message = update.effective_message
    if message is None or context.chat_data is None:
        return
    context.chat_data["awaiting"] = "add_duty_paste"
    await message.reply_text(
        "Paste the duty list you want to import. I will parse it and show a preview before saving anything."
    )


async def handle_pasted_duty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse pasted duty text, resolve unknown names, and show a confirmation preview."""
    message = update.effective_message
    if message is None or message.text is None or context.chat_data is None:
        return

    try:
        parsed = parse_duty_text(message.text)
    except DutyParseError as exc:
        await message.reply_text(
            f"Unable to parse line {exc.line_number}:\n\n{exc.line_text}\n\nExpected:\n{exc.expected}"
        )
        return

    context.chat_data.pop("awaiting", None)

    async with UnitOfWork() as uow:
        resolution = await _import_service.resolve_names(uow, parsed)

    context.chat_data["import_parsed"] = parsed
    context.chat_data["import_known_ids"] = {name: p.id for name, p in resolution.known.items()}
    context.chat_data["import_unknown"] = list(resolution.unknown)
    context.chat_data["import_ignored"] = []

    if resolution.unknown:
        await _prompt_next_unknown(message.reply_text, context)
        return

    await _show_final_preview(message.reply_text, context)


async def _prompt_next_unknown(reply_func: ReplyFunc, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert context.chat_data is not None
    unknown: list[str] = context.chat_data["import_unknown"]
    if not unknown:
        await _show_final_preview(reply_func, context)
        return
    name = unknown[0]
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Create", callback_data=f"import:create:{name}")],
            [InlineKeyboardButton("Match Existing", callback_data=f"import:match_menu:{name}")],
            [InlineKeyboardButton("Ignore", callback_data=f"import:ignore:{name}")],
        ]
    )
    await reply_func(f"Unknown person: {name}\n\nWhat would you like to do?", reply_markup=keyboard)


async def _show_final_preview(reply_func: ReplyFunc, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert context.chat_data is not None
    parsed: ParsedDuty = context.chat_data["import_parsed"]
    text = _render_preview(parsed)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Confirm", callback_data="import:confirm"),
                InlineKeyboardButton("Cancel", callback_data="import:cancel"),
            ]
        ]
    )
    await reply_func(f"{text}\n\nConfirm?", reply_markup=keyboard)


def _reply_func_for(query: CallbackQuery) -> ReplyFunc:
    """Return a ``reply_text``-compatible callable for the query's message."""
    message = query.message
    if isinstance(message, Message):
        return message.reply_text
    raise ImportServiceError("The original message is no longer accessible.")


@log_errors
@admin_only
async def import_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline-button presses for the /add_duty resolution workflow."""
    query = update.callback_query
    if query is None or query.data is None or context.chat_data is None:
        return
    await query.answer()

    parts = query.data.split(":", 2)
    action = parts[1]

    if action == "create":
        name = parts[2]
        async with UnitOfWork() as uow:
            person = await _personnel_service.add_person(uow, name)
        context.chat_data["import_known_ids"][name] = person.id
        context.chat_data["import_unknown"].remove(name)
        await query.edit_message_text(f"Created new person: {name}")
        await _prompt_next_unknown(_reply_func_for(query), context)

    elif action == "ignore":
        name = parts[2]
        context.chat_data["import_unknown"].remove(name)
        context.chat_data["import_ignored"].append(name)
        await query.edit_message_text(f"Ignored: {name} (their duty entries will be dropped)")
        await _prompt_next_unknown(_reply_func_for(query), context)

    elif action == "match_menu":
        name = parts[2]
        async with UnitOfWork() as uow:
            candidates = await uow.personnel.search_by_name("")
        buttons = [
            [InlineKeyboardButton(p.name, callback_data=f"import:matchto:{name}:{p.id}")] for p in candidates
        ]
        buttons.append([InlineKeyboardButton("Back", callback_data=f"import:back:{name}")])
        await query.edit_message_text(f"Match '{name}' to which existing person?", reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "matchto":
        name, person_id_raw = query.data.split(":", 3)[2:4]
        person_id = int(person_id_raw)
        context.chat_data["import_known_ids"][name] = person_id
        context.chat_data["import_unknown"].remove(name)
        await query.edit_message_text(f"Matched '{name}' to existing person id={person_id}.")
        await _prompt_next_unknown(_reply_func_for(query), context)

    elif action == "back":
        await _prompt_next_unknown(_reply_func_for(query), context)

    elif action == "confirm":
        parsed: ParsedDuty | None = context.chat_data.get("import_parsed")
        known_ids: dict[str, int] = context.chat_data.get("import_known_ids", {})
        if parsed is None:
            await query.edit_message_text("Nothing to confirm; the import session expired.")
            return
        async with UnitOfWork() as uow:
            name_to_person: dict[str, Personnel] = {}
            for name in parsed.all_names():
                known_person_id = known_ids.get(name)
                if known_person_id is not None:
                    matched_person = await uow.personnel.get_by_id(known_person_id)
                    if matched_person is not None:
                        name_to_person[name] = matched_person
            try:
                week = await _import_service.save_import(uow, parsed, name_to_person)
            except ImportServiceError as exc:
                await query.edit_message_text(str(exc))
                return
        await query.edit_message_text(f"Week {week.week_number} imported and saved.")
        _clear_import_state(context)

    elif action == "cancel":
        await query.edit_message_text("Import cancelled. Nothing was saved.")
        _clear_import_state(context)


def _clear_import_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.chat_data is None:
        return
    for key in ("import_parsed", "import_known_ids", "import_unknown", "import_ignored", "awaiting"):
        context.chat_data.pop(key, None)
