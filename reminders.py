"""Scheduled messages, using APScheduler:
- reminders before a visit (24 hours and 2 hours before);
- a rating request 2 hours after the visit was marked as done;
- marking visits as done automatically 2 hours after they end.

APScheduler keeps its jobs in memory, so they disappear when the bot stops.
That's why the database remembers what was already sent
(reminder_24h_sent / reminder_2h_sent / review_sent), and on every start
restore_reminders() and restore_review_requests() plan again everything still waiting.
"""

import logging
from datetime import timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
from config import (
    AUTO_COMPLETE_CHECK_MINUTES,
    AUTO_COMPLETE_HOURS,
    DATETIME_FORMAT,
    REMINDERS,
    REVIEW_DELAY_HOURS,
    TIMEZONE,
)
from keyboards import rating_kb, reminder_kb
from slots import now_local, to_datetime
from texts import get_text
from utils import booking_summary

# One scheduler for the whole bot. It works in Kyiv time.
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


def job_id(booking_id: int, kind: str) -> str:
    """Unique job name, e.g. 'reminder_15_24h'. Lets us find and remove the job later."""
    return f"reminder_{booking_id}_{kind}"


async def schedule_reminders(bot: Bot, booking, restoring: bool = False) -> None:
    """Plan the 24h and 2h reminders for one booking.

    restoring=False - a new booking was just made
    restoring=True  - the bot has just started and restores old reminders
    """
    start = to_datetime(booking["start_at"])
    now = now_local()

    for kind, hours in REMINDERS.items():
        if booking[f"reminder_{kind}_sent"]:
            continue  # already sent earlier

        run_at = start - timedelta(hours=hours)

        if run_at <= now:
            # The reminder time has already passed. Two possible reasons:
            # 1) a new booking made less than 24h/2h before the visit -
            #    this reminder is not needed at all;
            # 2) the bot was turned off at that moment - send it now,
            #    but skip the 24h one if it's already time for the 2h one.
            two_hours_before = start - timedelta(hours=REMINDERS["2h"])
            not_needed = not restoring or (kind == "24h" and now >= two_hours_before)
            if not_needed:
                await db.mark_reminder_sent(booking["id"], kind)
                continue
            run_at = now + timedelta(seconds=5)

        scheduler.add_job(
            send_reminder,
            trigger="date",                           # run once at a given time
            run_date=run_at.replace(tzinfo=TIMEZONE),  # this time is Kyiv time
            args=[bot, booking["id"], kind],
            id=job_id(booking["id"], kind),
            replace_existing=True,                    # don't create duplicates
        )
        logging.info("Reminder %s planned at %s", job_id(booking["id"], kind), run_at)


def remove_reminders(booking_id: int) -> None:
    """Delete planned reminders (when a booking is cancelled)."""
    for kind in REMINDERS:
        job = scheduler.get_job(job_id(booking_id, kind))
        if job:
            job.remove()


async def send_reminder_message(bot: Bot, booking, kind: str) -> None:
    """Just send the reminder message to the client (no checks, no marks)."""
    lang = await db.get_lang(booking["user_id"])
    summary = await booking_summary(lang, booking)
    text = get_text(lang, f"reminder_{kind}", summary=summary)
    await bot.send_message(booking["user_id"], text, reply_markup=reminder_kb(lang, booking["id"]))


async def send_reminder(bot: Bot, booking_id: int, kind: str) -> None:
    """Called by the scheduler at the right time."""
    booking = await db.get_booking(booking_id)
    if booking is None or booking["status"] != "active":
        return  # booking was cancelled - nothing to remind about

    try:
        await send_reminder_message(bot, booking, kind)
    except TelegramAPIError as error:
        # E.g. the client blocked the bot
        logging.warning("Could not send reminder for booking %s: %s", booking_id, error)

    # Mark as sent even after an error, so we don't try again and again
    await db.mark_reminder_sent(booking_id, kind)


async def restore_reminders(bot: Bot) -> None:
    """On bot start: plan reminders for all future bookings again."""
    now = now_local().strftime(DATETIME_FORMAT)
    bookings = await db.get_all_upcoming_bookings(now)
    for booking in bookings:
        await schedule_reminders(bot, booking, restoring=True)
    logging.info("Reminders restored for %s upcoming bookings", len(bookings))


# ---------- Rating request after the visit ----------

def schedule_review_request(bot: Bot, booking) -> None:
    """Plan the "Rate your visit" message at booking["review_at"]."""
    run_at = to_datetime(booking["review_at"])
    now = now_local()
    if run_at <= now:
        run_at = now + timedelta(seconds=5)  # missed while the bot was off - send soon

    scheduler.add_job(
        send_review_request,
        trigger="date",
        run_date=run_at.replace(tzinfo=TIMEZONE),
        args=[bot, booking["id"]],
        id=f"review_{booking['id']}",
        replace_existing=True,
    )
    logging.info("Review request for booking %s planned at %s", booking["id"], run_at)


async def send_review_message(bot: Bot, booking) -> None:
    """Just send "How was your visit?" with 1-5 ⭐ buttons."""
    lang = await db.get_lang(booking["user_id"])
    summary = await booking_summary(lang, booking)
    text = get_text(lang, "review_request", summary=summary)
    await bot.send_message(booking["user_id"], text, reply_markup=rating_kb(booking["id"]))


async def send_review_request(bot: Bot, booking_id: int) -> None:
    """Called by the scheduler."""
    booking = await db.get_booking(booking_id)
    if booking is None or booking["status"] != "completed" or booking["rating"]:
        return

    try:
        await send_review_message(bot, booking)
    except TelegramAPIError as error:
        logging.warning("Could not send review request for booking %s: %s", booking_id, error)

    await db.mark_review_sent(booking_id)


async def restore_review_requests(bot: Bot) -> None:
    """On bot start: plan rating requests that were not sent yet."""
    bookings = await db.get_pending_review_requests()
    for booking in bookings:
        schedule_review_request(bot, booking)
    logging.info("Review requests restored: %s", len(bookings))


# ---------- Auto-complete visits ----------

async def auto_complete_bookings(bot: Bot) -> None:
    """Mark as done every active visit that ended AUTO_COMPLETE_HOURS ago.

    Runs every AUTO_COMPLETE_CHECK_MINUTES minutes and once right after the bot starts.
    If the client didn't come, the admin should cancel the booking before that.
    """
    now = now_local()
    ended_before = now - timedelta(hours=AUTO_COMPLETE_HOURS)
    bookings = await db.get_bookings_to_auto_complete(ended_before.strftime(DATETIME_FORMAT))

    for booking in bookings:
        end = to_datetime(booking["end_at"])

        # Ask for a rating at the same time as for a visit marked by hand:
        # REVIEW_DELAY_HOURS after the end. If that's already past - send soon.
        # But if the visit was more than a day ago (the bot was off for long),
        # don't ask at all - the client has forgotten the details already.
        if now - end < timedelta(days=1):
            review_at = (end + timedelta(hours=REVIEW_DELAY_HOURS)).strftime(DATETIME_FORMAT)
        else:
            review_at = None

        await db.complete_booking(booking["id"], review_at)
        remove_reminders(booking["id"])
        if review_at:
            schedule_review_request(bot, await db.get_booking(booking["id"]))
        logging.info("Booking %s auto-completed", booking["id"])


def start_auto_complete(bot: Bot) -> None:
    """Run auto_complete_bookings now and then every few minutes."""
    scheduler.add_job(
        auto_complete_bookings,
        trigger="interval",                       # repeat again and again
        minutes=AUTO_COMPLETE_CHECK_MINUTES,
        args=[bot],
        id="auto_complete",
        replace_existing=True,
        next_run_time=now_local().replace(tzinfo=TIMEZONE),  # first run right away
    )
