"""Booking flow: branch -> service -> master -> date -> time -> confirm.

The whole flow happens in ONE message: on every step we edit it
instead of sending a new one, so the chat stays clean.
What the user has chosen so far is kept in FSM data (state.update_data).
"""

import logging
from datetime import date, timedelta

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

import database as db
from config import DATETIME_FORMAT
from keyboards import (
    back_kb,
    branches_kb,
    confirm_kb,
    dates_kb,
    master_kb,
    services_kb,
    times_kb,
)
from reminders import schedule_reminders
from slots import combine, get_free_slots, now_local, to_datetime, upcoming_days
from states import BookingStates
from texts import all_texts, format_date, get_text
from utils import build_summary, notify_admins

router = Router()


# =====================================================================
# Helpers for showing a step
# =====================================================================

async def show_text(callback: CallbackQuery, text: str, kb=None) -> None:
    """Show a text step in place of the current message.

    A photo message can't be turned into a text message,
    so in that case we delete it and send a new one.
    """
    message = callback.message
    if message.photo:
        await message.delete()
        await message.answer(text, reply_markup=kb)
    else:
        await message.edit_text(text, reply_markup=kb)


async def show_photo(callback: CallbackQuery, photo_url: str, caption: str, kb) -> None:
    """Show a photo with a caption in place of the current message."""
    message = callback.message
    try:
        if message.photo:
            # Photo -> another photo: just replace the picture and caption
            await message.edit_media(
                InputMediaPhoto(media=photo_url, caption=caption), reply_markup=kb
            )
        else:
            # Text -> photo: send a new photo message and delete the old text
            await message.answer_photo(photo_url, caption=caption, reply_markup=kb)
            await message.delete()
    except TelegramBadRequest:
        # Telegram could not load the picture (broken link) - show text instead
        logging.warning("Could not show photo %s", photo_url)
        await show_text(callback, caption, kb)


async def find_free_slots(master, service, day: date) -> list:
    """Free start times of a master on a day, considering the service length."""
    if await db.is_day_off(master["id"], day.isoformat()):
        return []  # the admin closed this day
    bookings = await db.get_master_bookings_for_day(master["id"], day.isoformat())
    busy = [(to_datetime(b["start_at"]), to_datetime(b["end_at"])) for b in bookings]
    return get_free_slots(day, master["work_start"], master["work_end"], service["duration"], busy)


async def summary_from_data(lang: str, data: dict) -> str:
    """Booking details from what the user has chosen so far (FSM data)."""
    start = combine(date.fromisoformat(data["date"]), data["time"])
    return await build_summary(lang, data["branch_id"], data["service_id"], data["master_id"], start)


# =====================================================================
# Steps. Each go_to_* function sets the state and shows the step.
# "Back" buttons simply call the previous go_to_* function.
# =====================================================================

async def go_to_branches(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    branches = await db.get_branches()
    await state.set_state(BookingStates.choosing_branch)
    await show_text(callback, get_text(lang, "choose_branch"), branches_kb(lang, branches))


async def go_to_services(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    services = await db.get_services_for_branch(data["branch_id"])
    await state.set_state(BookingStates.choosing_service)
    await show_text(callback, get_text(lang, "choose_service"), services_kb(lang, services))


async def go_to_masters(callback: CallbackQuery, state: FSMContext, lang: str, index: int = 0) -> None:
    data = await state.get_data()
    masters = await db.get_masters(data["branch_id"], data["service_id"])
    await state.set_state(BookingStates.choosing_master)

    if not masters:
        await show_text(callback, get_text(lang, "no_masters"), back_kb(lang))
        return

    # Wrap around: -1 becomes the last master, len(masters) becomes the first
    index = index % len(masters)
    master = masters[index]

    caption = get_text(
        lang,
        "master_card",
        counter=f"{index + 1}/{len(masters)}",
        name=master["name"],
        description=master[f"description_{lang}"] or "",
    )
    kb = master_kb(lang, master, index, len(masters))

    if master["photo_url"]:
        await show_photo(callback, master["photo_url"], caption, kb)
    else:
        await show_text(callback, caption, kb)


async def go_to_dates(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    master = await db.get_master(data["master_id"])
    service = await db.get_service(data["service_id"])
    await state.set_state(BookingStates.choosing_date)

    # Show only days that still have at least one free slot
    days = [day for day in upcoming_days() if await find_free_slots(master, service, day)]

    if not days:
        await show_text(callback, get_text(lang, "no_dates", name=master["name"]), back_kb(lang))
        return

    today = now_local().date()
    await show_text(callback, get_text(lang, "choose_date"), dates_kb(lang, days, today))


async def go_to_times(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    master = await db.get_master(data["master_id"])
    service = await db.get_service(data["service_id"])
    day = date.fromisoformat(data["date"])
    await state.set_state(BookingStates.choosing_time)

    slots = await find_free_slots(master, service, day)
    if not slots:
        await show_text(callback, get_text(lang, "no_times"), back_kb(lang))
        return

    text = get_text(lang, "choose_time", date=format_date(lang, day))
    await show_text(callback, text, times_kb(lang, slots))


async def go_to_confirm(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    await state.set_state(BookingStates.confirming)
    summary = await summary_from_data(lang, data)
    await show_text(callback, get_text(lang, "confirm_booking", summary=summary), confirm_kb(lang))


# =====================================================================
# Handlers
# =====================================================================

@router.message(F.text.in_(all_texts("btn_book")))
async def start_booking(message: Message, state: FSMContext) -> None:
    """User pressed "✂️ Book an appointment" in the main menu."""
    lang = await db.get_lang(message.from_user.id)
    await state.clear()  # forget any previous unfinished booking
    await state.set_state(BookingStates.choosing_branch)

    branches = await db.get_branches()
    await message.answer(get_text(lang, "choose_branch"), reply_markup=branches_kb(lang, branches))


@router.callback_query(BookingStates.choosing_branch, F.data.startswith("branch:"))
async def branch_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_lang(callback.from_user.id)
    branch_id = int(callback.data.split(":", 1)[1])  # "branch:2" -> 2
    await state.update_data(branch_id=branch_id)
    await go_to_services(callback, state, lang)
    await callback.answer()


@router.callback_query(BookingStates.choosing_service, F.data.startswith("service:"))
async def service_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_lang(callback.from_user.id)
    service_id = int(callback.data.split(":", 1)[1])
    await state.update_data(service_id=service_id)
    await go_to_masters(callback, state, lang, index=0)
    await callback.answer()


@router.callback_query(BookingStates.choosing_master, F.data.startswith("master_page:"))
async def master_page(callback: CallbackQuery, state: FSMContext) -> None:
    """◀️ / ▶️ arrows: show the previous / next master."""
    lang = await db.get_lang(callback.from_user.id)
    index = int(callback.data.split(":", 1)[1])
    await go_to_masters(callback, state, lang, index=index)
    await callback.answer()


@router.callback_query(BookingStates.choosing_master, F.data.startswith("master:"))
async def master_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_lang(callback.from_user.id)
    master_id = int(callback.data.split(":", 1)[1])
    await state.update_data(master_id=master_id)
    await go_to_dates(callback, state, lang)
    await callback.answer()


@router.callback_query(BookingStates.choosing_date, F.data.startswith("date:"))
async def date_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_lang(callback.from_user.id)
    await state.update_data(date=callback.data.split(":", 1)[1])  # "2026-11-12"
    await go_to_times(callback, state, lang)
    await callback.answer()


@router.callback_query(BookingStates.choosing_time, F.data.startswith("time:"))
async def time_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_lang(callback.from_user.id)
    # split(":", 1) splits only at the FIRST ":" -> "time:14:30" -> "14:30"
    await state.update_data(time=callback.data.split(":", 1)[1])
    await go_to_confirm(callback, state, lang)
    await callback.answer()


@router.callback_query(BookingStates.confirming, F.data == "confirm")
async def booking_confirmed(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    lang = await db.get_lang(callback.from_user.id)
    data = await state.get_data()
    service = await db.get_service(data["service_id"])

    start = combine(date.fromisoformat(data["date"]), data["time"])
    end = start + timedelta(minutes=service["duration"])

    # While the user was thinking, the time could become past,
    # or the admin could close this day
    if start <= now_local() or await db.is_day_off(data["master_id"], data["date"]):
        await callback.answer(get_text(lang, "slot_taken"), show_alert=True)
        await go_to_times(callback, state, lang)
        return

    booking_id = await db.create_booking(
        user_id=callback.from_user.id,
        branch_id=data["branch_id"],
        master_id=data["master_id"],
        service_id=data["service_id"],
        start_at=start.strftime(DATETIME_FORMAT),
        end_at=end.strftime(DATETIME_FORMAT),
        client_name=callback.from_user.full_name,
    )

    if booking_id is None:
        # Someone else took this time a moment ago
        await callback.answer(get_text(lang, "slot_taken"), show_alert=True)
        await go_to_times(callback, state, lang)
        return

    await state.clear()
    summary = await summary_from_data(lang, data)
    await show_text(callback, get_text(lang, "booking_done", summary=summary))
    await callback.answer()

    booking = await db.get_booking(booking_id)
    await schedule_reminders(bot, booking)  # plan 24h and 2h reminders
    await notify_admins(bot, "admin_new_booking", booking, callback.from_user)


@router.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext) -> None:
    """ "⬅️ Back": look at the current step and open the previous one."""
    lang = await db.get_lang(callback.from_user.id)
    current = await state.get_state()

    if current == BookingStates.choosing_service.state:
        await go_to_branches(callback, state, lang)
    elif current == BookingStates.choosing_master.state:
        await go_to_services(callback, state, lang)
    elif current == BookingStates.choosing_date.state:
        await go_to_masters(callback, state, lang)
    elif current == BookingStates.choosing_time.state:
        await go_to_dates(callback, state, lang)
    elif current == BookingStates.confirming.state:
        await go_to_times(callback, state, lang)
    else:
        # Not in the booking flow (e.g. the bot was restarted) - old button
        await callback.answer(get_text(lang, "button_outdated"))
        return

    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_booking(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_lang(callback.from_user.id)
    await state.clear()
    await show_text(callback, get_text(lang, "booking_cancelled"))
    await callback.answer()
