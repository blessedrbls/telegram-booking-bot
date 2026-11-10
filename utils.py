"""Helpers used in several handlers: booking texts and admin notifications."""

import html
import logging
from datetime import datetime
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import User

import database as db
from config import ADMIN_IDS
from slots import to_datetime
from texts import format_date, get_text, stars


async def build_summary(
    lang: str, branch_id: int, service_id: int, master_id: int, start: datetime
) -> str:
    """Text with all details of a booking: branch, service, price, master, date."""
    branch = await db.get_branch(branch_id)
    service = await db.get_service(service_id)
    master = await db.get_master(master_id)
    return get_text(
        lang,
        "booking_summary",
        branch=branch[f"name_{lang}"],
        address=branch[f"address_{lang}"],
        service=service[f"name_{lang}"],
        price=service["price"],
        duration=service["duration"],
        master=master["name"],
        date=format_date(lang, start.date()),
        time=start.strftime("%H:%M"),
    )


async def booking_summary(lang: str, booking) -> str:
    """Same as build_summary, but for a booking row from the database."""
    return await build_summary(
        lang,
        booking["branch_id"],
        booking["service_id"],
        booking["master_id"],
        to_datetime(booking["start_at"]),
    )


def make_client_link(user_id: int, name: str, username: Optional[str]) -> str:
    """Clickable client name for admins, e.g. 'Oleksii (@nick)'."""
    # html.escape protects the message markup from names like "<b>Bob"
    text = f'<a href="tg://user?id={user_id}">{html.escape(name or str(user_id))}</a>'
    if username:
        text += f" (@{username})"
    return text


def client_link(user: User) -> str:
    """Same, but from a Telegram User object."""
    return make_client_link(user.id, user.full_name, user.username)


async def admin_booking_card(lang: str, booking) -> str:
    """Short booking card for the admin list (booking row must have 'username')."""
    branch = await db.get_branch(booking["branch_id"])
    service = await db.get_service(booking["service_id"])
    master = await db.get_master(booking["master_id"])

    text = get_text(
        lang,
        "adm_booking_card",
        id=booking["id"],
        start=to_datetime(booking["start_at"]).strftime("%H:%M"),
        end=to_datetime(booking["end_at"]).strftime("%H:%M"),
        master=master["name"],
        service=service[f"name_{lang}"],
        price=service["price"],
        branch=branch[f"name_{lang}"],
        client=make_client_link(booking["user_id"], booking["client_name"], booking["username"]),
    )

    # Extra lines depending on the booking state
    if booking["confirmed"] and booking["status"] == "active":
        text += "\n" + get_text(lang, "adm_mark_confirmed")
    if booking["status"] == "completed":
        text += "\n\n" + get_text(lang, "adm_mark_done")
    if booking["rating"]:
        text += "\n" + get_text(lang, "adm_mark_rating", stars=stars(booking["rating"]))
    return text


async def notify_admins(bot: Bot, text_key: str, booking, client: User, **extra) -> None:
    """Send every admin a message about a booking (new / cancelled / feedback).

    **extra - additional values for the text, e.g. feedback="..." for a review.
    """
    for admin_id in ADMIN_IDS:
        lang = await db.get_lang(admin_id)  # each admin gets their own language
        summary = await booking_summary(lang, booking)
        text = get_text(
            lang, text_key, id=booking["id"], client=client_link(client), summary=summary, **extra
        )
        try:
            await bot.send_message(admin_id, text)
        except TelegramAPIError as error:
            # E.g. the admin never pressed /start in this bot - Telegram forbids messaging them
            logging.warning("Could not notify admin %s: %s", admin_id, error)
