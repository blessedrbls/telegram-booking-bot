"""Handlers for regular users (clients)."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from config import DEFAULT_LANGUAGE, LANGUAGES
from keyboards import branch_kb, language_kb, main_menu_kb
from texts import all_texts, get_text

router = Router()

# Short name, so handlers can write `await get_lang(...)`
get_lang = db.get_lang


async def send_main_menu(message: Message, lang: str) -> None:
    """Send the greeting with the main menu keyboard."""
    await message.answer(get_text(lang, "welcome"), reply_markup=main_menu_kb(lang))


# ---------- /start ----------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()  # cancel any unfinished dialog
    await db.add_user(message.from_user.id, message.from_user.username)

    lang = await db.get_user_language(message.from_user.id)
    if lang is None:
        # First visit: ask for the language first
        await message.answer(
            get_text(DEFAULT_LANGUAGE, "choose_language"), reply_markup=language_kb()
        )
        return

    await send_main_menu(message, lang)


# ---------- Language ----------

@router.message(Command("language"))
@router.message(F.text.in_(all_texts("btn_language")))
async def cmd_language(message: Message) -> None:
    lang = await get_lang(message.from_user.id)
    await message.answer(get_text(lang, "choose_language"), reply_markup=language_kb())


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":")[1]  # "lang:uk" -> "uk"
    if lang not in LANGUAGES:
        await callback.answer()
        return

    await db.set_user_language(callback.from_user.id, lang)

    # Replace the language buttons with a confirmation text
    await callback.message.edit_text(get_text(lang, "language_set"))
    await send_main_menu(callback.message, lang)
    await callback.answer()  # stop the "loading" clock on the button


# ---------- Our locations ----------

@router.message(F.text.in_(all_texts("btn_locations")))
async def show_locations(message: Message) -> None:
    lang = await get_lang(message.from_user.id)
    branches = await db.get_branches()

    if not branches:
        await message.answer(get_text(lang, "no_branches"))
        return

    await message.answer(get_text(lang, "locations_title"))

    # One message per branch, each with its own Google Maps button
    for branch in branches:
        hours = get_text(
            lang, "branch_hours", open=branch["open_time"], close=branch["close_time"]
        )
        text = get_text(
            lang,
            "branch_card",
            name=branch[f"name_{lang}"],        # name_en or name_uk
            address=branch[f"address_{lang}"],  # address_en or address_uk
            hours=hours,
        )
        await message.answer(text, reply_markup=branch_kb(lang, branch["maps_url"]))


# ---------- Anything else ----------
# These handlers must stay LAST: they catch everything that was not handled above.

@router.message()
async def unknown_message(message: Message) -> None:
    lang = await get_lang(message.from_user.id)
    await message.answer(get_text(lang, "use_menu"), reply_markup=main_menu_kb(lang))


@router.callback_query()
async def outdated_button(callback: CallbackQuery) -> None:
    """A button from an old message (e.g. after the bot restarted)."""
    lang = await get_lang(callback.from_user.id)
    await callback.answer(get_text(lang, "button_outdated"))
