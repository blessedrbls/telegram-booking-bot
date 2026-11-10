"""Admin panel. Only users from ADMIN_IDS can reach these handlers.

/admin opens a menu:
  📅 Today / 📅 Tomorrow - bookings of the day with "Done" and "Cancel" buttons
  📆 Choose a date      - the same for any of the next 7 days
  📋 All upcoming       - short list of all future bookings
  🚫 Days off           - close or open a day for a master
"""

import logging
from datetime import date, timedelta

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import database as db
from config import ADMIN_IDS, DATETIME_FORMAT, REVIEW_DELAY_HOURS
from keyboards import (
    admin_booking_kb,
    admin_cancel_confirm_kb,
    admin_dates_kb,
    admin_days_off_kb,
    admin_masters_kb,
    admin_menu_kb,
    day_label,
)
from reminders import (
    remove_reminders,
    schedule_review_request,
    send_reminder_message,
    send_review_message,
)
from slots import now_local, to_datetime, upcoming_days
from texts import get_text
from utils import admin_booking_card, booking_summary, make_client_link

router = Router()

# Filters for the whole router: messages and button presses from non-admins skip it
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


# =====================================================================
# Menu
# =====================================================================

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    lang = await db.get_lang(message.from_user.id)
    await message.answer(get_text(lang, "admin_menu"), reply_markup=admin_menu_kb(lang))


@router.callback_query(F.data == "adm:menu")
async def back_to_menu(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    await callback.message.edit_text(get_text(lang, "admin_menu"), reply_markup=admin_menu_kb(lang))
    await callback.answer()


# =====================================================================
# Bookings of today / tomorrow
# =====================================================================

async def send_day_bookings(callback: CallbackQuery, day: date, lang: str) -> None:
    """Send the bookings of one day: a header and one card per booking."""
    today = now_local().date()
    day_text = day_label(lang, day, today)  # "Today, 10.11"

    bookings = await db.get_bookings_for_day(day.isoformat())
    if not bookings:
        await callback.message.answer(get_text(lang, "adm_no_bookings_day", day=day_text))
        return

    await callback.message.answer(
        get_text(lang, "adm_day_header", day=day_text, count=len(bookings))
    )
    # One message per booking. Buttons only for active ones (not done yet).
    for booking in bookings:
        card = await admin_booking_card(lang, booking)
        kb = admin_booking_kb(lang, booking["id"]) if booking["status"] == "active" else None
        await callback.message.answer(card, reply_markup=kb)


@router.callback_query(F.data.in_({"adm:today", "adm:tomorrow"}))
async def show_today_or_tomorrow(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    today = now_local().date()
    day = today if callback.data == "adm:today" else today + timedelta(days=1)
    await send_day_bookings(callback, day, lang)
    await callback.answer()


# ---------- 📆 Choose a date ----------

@router.callback_query(F.data == "adm:pick_date")
async def pick_date(callback: CallbackQuery) -> None:
    """Show the next 7 days with the number of bookings on each."""
    lang = await db.get_lang(callback.from_user.id)
    today = now_local().date()
    counts = await db.get_booking_counts(today.isoformat())
    await callback.message.edit_text(
        get_text(lang, "adm_pick_date"),
        reply_markup=admin_dates_kb(lang, upcoming_days(), counts, today),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_date:"))
async def date_picked(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    day = date.fromisoformat(callback.data.split(":")[1])  # "adm_date:2026-11-16"
    await send_day_bookings(callback, day, lang)
    await callback.answer()


# ---------- 📋 All upcoming ----------

@router.callback_query(F.data == "adm:all")
async def show_all_upcoming(callback: CallbackQuery) -> None:
    """Short list of all active bookings from today, grouped by day.

    Without buttons - to manage a booking the admin opens its day.
    """
    lang = await db.get_lang(callback.from_user.id)
    today = now_local().date()
    bookings = await db.get_active_bookings_from(today.isoformat())

    if not bookings:
        await callback.message.answer(get_text(lang, "adm_all_empty"))
        await callback.answer()
        return

    lines = [get_text(lang, "adm_all_header", count=len(bookings))]
    current_day = None
    for booking in bookings:
        start = to_datetime(booking["start_at"])

        # New day -> add a day title before its bookings
        if start.date() != current_day:
            current_day = start.date()
            lines.append(f"\n📅 <b>{day_label(lang, current_day, today)}</b>")

        master = await db.get_master(booking["master_id"])
        service = await db.get_service(booking["service_id"])
        lines.append(get_text(
            lang,
            "adm_all_line",
            id=booking["id"],
            start=start.strftime("%H:%M"),
            end=to_datetime(booking["end_at"]).strftime("%H:%M"),
            master=master["name"],
            service=service[f"name_{lang}"],
            client=make_client_link(booking["user_id"], booking["client_name"], booking["username"]),
        ))
    lines.append("\n" + get_text(lang, "adm_all_hint"))

    # A Telegram message can't be longer than 4096 characters,
    # so a long list is split into several messages
    message_text = ""
    for line in lines:
        if len(message_text) + len(line) > 3500:
            await callback.message.answer(message_text)
            message_text = ""
        message_text += line + "\n"
    await callback.message.answer(message_text)
    await callback.answer()


async def get_active_booking(callback: CallbackQuery, booking_id: int, lang: str):
    """Return the booking if it's still active, otherwise tell the admin and remove buttons."""
    booking = await db.get_booking(booking_id)
    if booking is not None and booking["status"] == "active":
        return booking

    await callback.answer(get_text(lang, "adm_not_active"), show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)
    return None


@router.callback_query(F.data.startswith("adm_done:"))
async def mark_done(callback: CallbackQuery, bot: Bot) -> None:
    lang = await db.get_lang(callback.from_user.id)
    booking_id = int(callback.data.split(":")[1])

    booking = await get_active_booking(callback, booking_id, lang)
    if booking is None:
        return

    # A visit from tomorrow can't be "done" yet
    if to_datetime(booking["start_at"]).date() > now_local().date():
        await callback.answer(get_text(lang, "adm_not_today"), show_alert=True)
        return

    # Ask the client for a rating REVIEW_DELAY_HOURS hours from now
    review_at = now_local() + timedelta(hours=REVIEW_DELAY_HOURS)
    await db.complete_booking(booking_id, review_at.strftime(DATETIME_FORMAT))
    remove_reminders(booking_id)  # the visit is over - no reminders needed

    booking = await db.get_booking(booking_id)  # read again with the new review_at
    schedule_review_request(bot, booking)

    new_text = callback.message.html_text + "\n\n" + get_text(lang, "adm_mark_done")
    await callback.message.edit_text(new_text)
    await callback.answer()


# ---------- Cancel: "❌ Cancel" -> "Yes / No" ----------

@router.callback_query(F.data.startswith("adm_cancel:"))
async def cancel_ask(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    booking_id = int(callback.data.split(":")[1])
    if await get_active_booking(callback, booking_id, lang) is None:
        return
    await callback.message.edit_reply_markup(reply_markup=admin_cancel_confirm_kb(lang, booking_id))
    await callback.answer()


@router.callback_query(F.data.startswith("adm_cancel_no:"))
async def cancel_no(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    booking_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup(reply_markup=admin_booking_kb(lang, booking_id))
    await callback.answer()


@router.callback_query(F.data.startswith("adm_cancel_yes:"))
async def cancel_yes(callback: CallbackQuery, bot: Bot) -> None:
    lang = await db.get_lang(callback.from_user.id)
    booking_id = int(callback.data.split(":")[1])

    booking = await get_active_booking(callback, booking_id, lang)
    if booking is None:
        return

    await db.cancel_booking(booking_id)
    remove_reminders(booking_id)

    new_text = callback.message.html_text + "\n\n" + get_text(lang, "adm_mark_cancelled")
    await callback.message.edit_text(new_text)
    await callback.answer()

    # Tell the client, in the client's language
    client_lang = await db.get_lang(booking["user_id"])
    summary = await booking_summary(client_lang, booking)
    text = get_text(client_lang, "client_cancelled_by_admin", id=booking_id, summary=summary)
    try:
        await bot.send_message(booking["user_id"], text)
    except TelegramAPIError as error:
        logging.warning("Could not tell client about cancel of booking %s: %s", booking_id, error)


# =====================================================================
# Days off
# =====================================================================

@router.callback_query(F.data == "adm:days_off")
async def choose_master(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    masters = await db.get_all_masters()
    await callback.message.edit_text(
        get_text(lang, "adm_choose_master"), reply_markup=admin_masters_kb(lang, masters)
    )
    await callback.answer()


async def show_master_days(callback: CallbackQuery, master_id: int, lang: str) -> None:
    """Show the next 7 days of a master; closed days have 🚫."""
    master = await db.get_master(master_id)
    closed = await db.get_days_off(master_id)
    today = now_local().date()
    await callback.message.edit_text(
        get_text(lang, "adm_choose_day_off", master=master["name"]),
        reply_markup=admin_days_off_kb(lang, master_id, upcoming_days(), closed, today),
    )


@router.callback_query(F.data.startswith("adm_master:"))
async def master_chosen(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    master_id = int(callback.data.split(":")[1])
    await show_master_days(callback, master_id, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_day:"))
async def toggle_day(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    _, master_id, day = callback.data.split(":")  # "adm_day:1:2026-11-12"
    master_id = int(master_id)

    closed_now = await db.toggle_day_off(master_id, day)

    if closed_now:
        # Existing bookings are NOT cancelled automatically - warn the admin
        bookings = await db.get_master_bookings_for_day(master_id, day)
        if bookings:
            await callback.answer(
                get_text(lang, "adm_day_closed_warning", count=len(bookings)), show_alert=True
            )
        else:
            await callback.answer(get_text(lang, "adm_day_closed"))
    else:
        await callback.answer(get_text(lang, "adm_day_opened"))

    await show_master_days(callback, master_id, lang)  # redraw the 🚫 marks


# =====================================================================
# Test commands (to check scheduled messages without waiting)
# =====================================================================

@router.message(Command("test_reminder"))
async def cmd_test_reminder(message: Message, bot: Bot) -> None:
    """Send a reminder for your nearest booking right now.

    It doesn't mark the reminder as sent, so the real reminders still come on time.
    """
    lang = await db.get_lang(message.from_user.id)
    now = now_local().strftime(DATETIME_FORMAT)
    bookings = await db.get_user_upcoming_bookings(message.from_user.id, now)

    if not bookings:
        await message.answer(get_text(lang, "no_bookings"))
        return

    await send_reminder_message(bot, bookings[0], "24h")  # bookings[0] = the nearest one


@router.message(Command("test_review"))
async def cmd_test_review(message: Message, bot: Bot) -> None:
    """Send "Rate your visit" for your latest completed booking right now."""
    lang = await db.get_lang(message.from_user.id)
    booking = await db.get_last_unrated_completed(message.from_user.id)

    if booking is None:
        await message.answer(get_text(lang, "adm_no_review_test"))
        return

    await send_review_message(bot, booking)
