"""Client rates a visit 1-5 ⭐.

4-5 ⭐ -> thank you + link to leave a review on Google Maps
1-3 ⭐ -> ask what went wrong, then send that text to admins
"""

import html

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from keyboards import review_link_kb
from states import ReviewStates
from texts import all_texts, get_text, stars
from utils import notify_admins

router = Router()

# Texts of the main menu buttons - they must keep working as buttons,
# not be saved as a review
MENU_TEXTS = (
    all_texts("btn_book")
    + all_texts("btn_my_bookings")
    + all_texts("btn_locations")
    + all_texts("btn_language")
)


@router.callback_query(F.data.startswith("rate:"))
async def rate_visit(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_lang(callback.from_user.id)
    _, booking_id, rating = callback.data.split(":")  # "rate:12:5"
    booking_id, rating = int(booking_id), int(rating)

    booking = await db.get_booking(booking_id)
    is_own_done = (
        booking is not None
        and booking["user_id"] == callback.from_user.id
        and booking["status"] == "completed"
    )
    if not is_own_done:
        await callback.answer(get_text(lang, "booking_not_active"), show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    if booking["rating"]:
        # Can't rate twice (e.g. the request was sent again by /test_review)
        await callback.answer(get_text(lang, "review_already"), show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    await db.set_rating(booking_id, rating)

    # Replace the ⭐ buttons with the chosen rating
    new_text = callback.message.html_text + "\n\n" + get_text(
        lang, "review_your_rating", stars=stars(rating)
    )
    await callback.message.edit_text(new_text)
    await callback.answer()

    if rating >= 4:
        # Happy client - ask for a public review on Google Maps
        branch = await db.get_branch(booking["branch_id"])
        await callback.message.answer(
            get_text(lang, "review_thanks_good"),
            reply_markup=review_link_kb(lang, branch["maps_url"]),
        )
    else:
        # Unhappy client - ask what went wrong and wait for their next message
        await state.set_state(ReviewStates.waiting_text)
        await state.update_data(review_booking_id=booking_id)
        await callback.message.answer(get_text(lang, "review_ask_text"))


@router.message(
    ReviewStates.waiting_text,
    F.text,                          # only text messages
    ~F.text.startswith("/"),         # not a command like /start
    ~F.text.in_(MENU_TEXTS),         # not a main menu button
)
async def review_text(message: Message, state: FSMContext, bot: Bot) -> None:
    lang = await db.get_lang(message.from_user.id)
    data = await state.get_data()
    booking_id = data["review_booking_id"]

    await db.set_review_text(booking_id, message.text)
    await state.clear()
    await message.answer(get_text(lang, "review_thanks_bad"))

    booking = await db.get_booking(booking_id)
    await notify_admins(
        bot,
        "admin_feedback",
        booking,
        message.from_user,
        stars=stars(booking["rating"]),
        feedback=html.escape(message.text),  # client text must not break the HTML markup
    )
