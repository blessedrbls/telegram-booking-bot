"""Entry point: run `python bot.py` to start the bot."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database import init_db
from handlers import admin, booking, my_bookings, review, user
from reminders import (
    restore_reminders,
    restore_review_requests,
    scheduler,
    start_auto_complete,
)
from texts import get_text


async def set_commands(bot: Bot) -> None:
    """Set the command list shown in Telegram's "Menu" button."""
    for lang in ["en", "uk"]:
        commands = [
            BotCommand(command="start", description=get_text(lang, "cmd_start")),
            BotCommand(command="language", description=get_text(lang, "cmd_language")),
        ]
        # English is the default for everyone; Ukrainian for Telegram set to Ukrainian
        language_code = None if lang == "en" else lang
        await bot.set_my_commands(commands, language_code=language_code)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty. Copy .env.example to .env and fill it in.")

    await init_db()

    # parse_mode=HTML lets us use <b>bold</b> in texts
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Order matters: user router has "catch-all" handlers, so it goes last
    dp.include_router(admin.router)
    dp.include_router(booking.router)
    dp.include_router(my_bookings.router)
    dp.include_router(review.router)
    dp.include_router(user.router)

    await set_commands(bot)

    # Start the scheduler and plan everything that is still waiting
    scheduler.start()
    await restore_reminders(bot)
    await restore_review_requests(bot)
    start_auto_complete(bot)  # mark finished visits as done every 10 minutes

    # Skip messages that were sent while the bot was offline
    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        # Runs when the bot stops (Ctrl+C)
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
