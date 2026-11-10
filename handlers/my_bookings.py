"""📋 My bookings: list of future bookings, cancelling, and reminder buttons."""

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

import database as db
from config import DATETIME_FORMAT
from keyboards import booking_item_kb, cancel_confirm_kb, reminder_kb
from reminders import remove_reminders
from slots import now_local, to_datetime
from texts import all_texts, get_text
from utils import booking_summary, notify_admins

router = Router()


async def get_own_active_booking(callback: CallbackQuery, booking_id: int, lang: str):
    """Return the booking if it belongs to this user and is still active.

    Otherwise tell the user and remove the old buttons.
    """
    booking = await db.get_booking(booking_id)
    is_ok = (
        booking is not None
        and booking["user_id"] == callback.from_user.id  # nobody can cancel someone else's booking
        and booking["status"] == "active"
        and to_datetime(booking["start_at"]) > now_local()
    )
    if is_ok:
        return booking

    await callback.answer(get_text(lang, "booking_not_active"), show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)
    return None


# ---------- List ----------

@router.message(F.text.in_(all_texts("btn_my_bookings")))
async def show_my_bookings(message: Message) -> None:
    lang = await db.get_lang(message.from_user.id)
    now = now_local().strftime(DATETIME_FORMAT)
    bookings = await db.get_user_upcoming_bookings(message.from_user.id, now)

    if not bookings:
        await message.answer(get_text(lang, "no_bookings"))
        return

    await message.answer(get_text(lang, "my_bookings_title"))

    # One message per booking, each with its own "Cancel" button
    for booking in bookings:
        summary = await booking_summary(lang, booking)
        text = get_text(lang, "booking_item", id=booking["id"], summary=summary)
        if booking["confirmed"]:
            text += "\n\n" + get_text(lang, "visit_confirmed_mark")
        await message.answer(text, reply_markup=booking_item_kb(lang, booking["id"]))


# ---------- Cancelling ----------
# Step 1: "❌ Cancel" -> show "Yes, cancel it" / "No, keep it"
# Step 2: "Yes" -> cancel the booking, "No" -> put the old buttons back

@router.callback_query(F.data.startswith("cancel_ask:"))
async def cancel_ask(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    _, booking_id, src = callback.data.split(":")  # "cancel_ask:12:list"
    booking_id = int(booking_id)

    if await get_own_active_booking(callback, booking_id, lang) is None:
        return

    await callback.message.edit_reply_markup(
        reply_markup=cancel_confirm_kb(lang, booking_id, src)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_no:"))
async def cancel_no(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    _, booking_id, src = callback.data.split(":")
    booking_id = int(booking_id)

    # Put back the buttons that were there before
    if src == "rem":
        kb = reminder_kb(lang, booking_id)
    else:
        kb = booking_item_kb(lang, booking_id)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_yes:"))
async def cancel_yes(callback: CallbackQuery, bot: Bot) -> None:
    lang = await db.get_lang(callback.from_user.id)
    booking_id = int(callback.data.split(":")[1])

    booking = await get_own_active_booking(callback, booking_id, lang)
    if booking is None:
        return

    await db.cancel_booking(booking_id)
    remove_reminders(booking_id)  # no reminders for a cancelled booking

    # Keep the old text (html_text keeps bold etc.), add a mark, remove buttons
    new_text = callback.message.html_text + "\n\n" + get_text(lang, "booking_cancelled_mark")
    await callback.message.edit_text(new_text)
    await callback.answer()

    await notify_admins(bot, "admin_booking_cancelled", booking, callback.from_user)


# ---------- "✅ I'll come" from a reminder ----------

@router.callback_query(F.data.startswith("come:"))
async def will_come(callback: CallbackQuery) -> None:
    lang = await db.get_lang(callback.from_user.id)
    booking_id = int(callback.data.split(":")[1])

    if await get_own_active_booking(callback, booking_id, lang) is None:
        return

    await db.confirm_visit(booking_id)
    new_text = callback.message.html_text + "\n\n" + get_text(lang, "visit_confirmed")
    await callback.message.edit_text(new_text)
    await callback.answer()
