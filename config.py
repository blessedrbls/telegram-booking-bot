"""Project settings. Secrets are read from the .env file."""

import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# Read variables from .env into the environment
load_dotenv()

# --- Secrets from .env ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ADMIN_IDS in .env looks like: 123456789,987654321
ADMIN_IDS = [
    int(admin_id)
    for admin_id in os.getenv("ADMIN_IDS", "").split(",")
    if admin_id.strip().isdigit()
]

# --- General settings ---
TIMEZONE_NAME = "Europe/Kyiv"
TIMEZONE = ZoneInfo(TIMEZONE_NAME)

DB_PATH = "booking.db"

# Languages supported by the bot. The first one is the default.
LANGUAGES = ["en", "uk"]
DEFAULT_LANGUAGE = "en"

# Default working hours for masters (used for demo data)
DEFAULT_WORK_START = "10:00"
DEFAULT_WORK_END = "20:00"

# --- Booking settings ---
SLOT_STEP_MINUTES = 30      # time slots: 10:00, 10:30, 11:00, ...
BOOKING_DAYS_AHEAD = 7      # how many days ahead a client can book

# Reminders: name -> how many hours before the visit to send it
REMINDERS = {"24h": 24, "2h": 2}

# Ask the client to rate the visit this many hours after it was marked as done
REVIEW_DELAY_HOURS = 2

# A visit is marked as done automatically this many hours after it ends
# (if the admin didn't mark it or cancel it by hand)
AUTO_COMPLETE_HOURS = 2
AUTO_COMPLETE_CHECK_MINUTES = 10   # how often the bot checks for such visits

# How dates are stored in the database (always Kyiv time)
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
