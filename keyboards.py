"""Functions that build keyboards (buttons) for the bot."""

from datetime import date, timedelta
from typing import List

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from texts import format_date, get_text


def language_kb() -> InlineKeyboardMarkup:
    """Inline buttons for choosing a language.

    callback_data looks like "lang:en" - we read the code after ":" in the handler.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
                InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang:uk"),
            ]
        ]
    )


def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    """Main menu: big buttons under the message input field."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, "btn_book"))],
            [
                KeyboardButton(text=get_text(lang, "btn_my_bookings")),
                KeyboardButton(text=get_text(lang, "btn_locations")),
            ],
            [KeyboardButton(text=get_text(lang, "btn_language"))],
        ],
        resize_keyboard=True,  # make buttons compact
        input_field_placeholder=get_text(lang, "menu_placeholder"),
    )


def branch_kb(lang: str, url: str) -> InlineKeyboardMarkup:
    """One button that opens the branch in Google Maps."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "btn_open_maps"), url=url)]
        ]
    )


# ---------- Booking ----------
# callback_data format: "<action>:<value>", e.g. "branch:1", "time:14:30".
# The handler splits it by the first ":" to get the value.

def split_rows(buttons: list, per_row: int) -> List[list]:
    """[b1, b2, b3, b4, b5], 2 -> [[b1, b2], [b3, b4], [b5]]."""
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def nav_row(lang: str, with_back: bool = True) -> list:
    """Row with "Back" and "Cancel" buttons, added under every booking step."""
    row = []
    if with_back:
        row.append(InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="back"))
    row.append(InlineKeyboardButton(text=get_text(lang, "btn_cancel"), callback_data="cancel"))
    return row


def back_kb(lang: str) -> InlineKeyboardMarkup:
    """Only "Back" and "Cancel" (used when there is nothing to choose)."""
    return InlineKeyboardMarkup(inline_keyboard=[nav_row(lang)])


def branches_kb(lang: str, branches: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=branch[f"name_{lang}"], callback_data=f"branch:{branch['id']}")]
        for branch in branches
    ]
    rows.append(nav_row(lang, with_back=False))  # first step: nothing to go back to
    return InlineKeyboardMarkup(inline_keyboard=rows)


def services_kb(lang: str, services: list) -> InlineKeyboardMarkup:
    rows = []
    for service in services:
        text = get_text(
            lang,
            "service_button",
            name=service[f"name_{lang}"],
            price=service["price"],
            duration=service["duration"],
        )
        rows.append([InlineKeyboardButton(text=text, callback_data=f"service:{service['id']}")])
    rows.append(nav_row(lang))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def master_kb(lang: str, master, index: int, total: int) -> InlineKeyboardMarkup:
    """Buttons under a master's photo: ◀️ [Choose] ▶️.

    The arrows switch between masters (a "carousel").
    Index wraps around in the handler: after the last master comes the first one.
    """
    choose = InlineKeyboardButton(
        text=get_text(lang, "btn_choose_master", name=master["name"]),
        callback_data=f"master:{master['id']}",
    )
    if total > 1:
        first_row = [
            InlineKeyboardButton(text="◀️", callback_data=f"master_page:{index - 1}"),
            choose,
            InlineKeyboardButton(text="▶️", callback_data=f"master_page:{index + 1}"),
        ]
    else:
        first_row = [choose]
    return InlineKeyboardMarkup(inline_keyboard=[first_row, nav_row(lang)])


def day_label(lang: str, day: date, today: date) -> str:
    """Button text for a date: 'Today, 10.11', 'Tomorrow, 11.11', 'Wed, 12.11'."""
    if day == today:
        return f"{get_text(lang, 'today')}, {day.strftime('%d.%m')}"
    if day == today + timedelta(days=1):
        return f"{get_text(lang, 'tomorrow')}, {day.strftime('%d.%m')}"
    return format_date(lang, day)


def dates_kb(lang: str, days: List[date], today: date) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=day_label(lang, day, today), callback_data=f"date:{day.isoformat()}")
        for day in days
    ]
    rows = split_rows(buttons, 2)
    rows.append(nav_row(lang))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def times_kb(lang: str, slots: List[str]) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=slot, callback_data=f"time:{slot}") for slot in slots]
    rows = split_rows(buttons, 4)
    rows.append(nav_row(lang))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "btn_confirm"), callback_data="confirm")],
            nav_row(lang),
        ]
    )


# ---------- My bookings and reminders ----------
# "src" tells where the buttons were shown: "list" (My bookings) or "rem" (reminder).
# We need it to put the right buttons back if the user says "No, keep it".

def booking_item_kb(lang: str, booking_id: int) -> InlineKeyboardMarkup:
    """Button under a booking in "My bookings"."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=get_text(lang, "btn_cancel_booking"),
                callback_data=f"cancel_ask:{booking_id}:list",
            )]
        ]
    )


def reminder_kb(lang: str, booking_id: int) -> InlineKeyboardMarkup:
    """Buttons under a reminder: ✅ I'll come / ❌ Cancel."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_will_come"),
                    callback_data=f"come:{booking_id}",
                ),
                InlineKeyboardButton(
                    text=get_text(lang, "btn_reminder_cancel"),
                    callback_data=f"cancel_ask:{booking_id}:rem",
                ),
            ]
        ]
    )


def cancel_confirm_kb(lang: str, booking_id: int, src: str) -> InlineKeyboardMarkup:
    """ "Are you sure?" buttons, so a booking is not cancelled by accident."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_cancel_yes"),
                    callback_data=f"cancel_yes:{booking_id}",
                ),
                InlineKeyboardButton(
                    text=get_text(lang, "btn_cancel_no"),
                    callback_data=f"cancel_no:{booking_id}:{src}",
                ),
            ]
        ]
    )


# ---------- Reviews ----------

def rating_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Five buttons in one row: 1⭐ 2⭐ 3⭐ 4⭐ 5⭐."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{n}⭐", callback_data=f"rate:{booking_id}:{n}")
                for n in range(1, 6)
            ]
        ]
    )


def review_link_kb(lang: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=get_text(lang, "btn_leave_review"), url=url)]]
    )


# ---------- Admin panel ----------
# All admin callback_data start with "adm", so they never mix with client buttons.

def admin_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text(lang, "btn_adm_today"), callback_data="adm:today"),
                InlineKeyboardButton(text=get_text(lang, "btn_adm_tomorrow"), callback_data="adm:tomorrow"),
            ],
            [
                InlineKeyboardButton(text=get_text(lang, "btn_adm_pick_date"), callback_data="adm:pick_date"),
                InlineKeyboardButton(text=get_text(lang, "btn_adm_all"), callback_data="adm:all"),
            ],
            [InlineKeyboardButton(text=get_text(lang, "btn_adm_days_off"), callback_data="adm:days_off")],
        ]
    )


def admin_dates_kb(lang: str, days: List[date], counts: dict, today: date) -> InlineKeyboardMarkup:
    """Dates for the admin, with the number of bookings: 'Thu, 12.11 · 3'."""
    buttons = []
    for day in days:
        label = day_label(lang, day, today)
        count = counts.get(day.isoformat(), 0)
        if count:
            label += f" · {count}"
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"adm_date:{day.isoformat()}"))
    rows = split_rows(buttons, 2)
    rows.append([InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_booking_kb(lang: str, booking_id: int) -> InlineKeyboardMarkup:
    """Buttons under a booking in the admin list."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text(lang, "btn_adm_done"), callback_data=f"adm_done:{booking_id}"),
                InlineKeyboardButton(text=get_text(lang, "btn_adm_cancel"), callback_data=f"adm_cancel:{booking_id}"),
            ]
        ]
    )


def admin_cancel_confirm_kb(lang: str, booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text(lang, "btn_adm_cancel_yes"), callback_data=f"adm_cancel_yes:{booking_id}"),
                InlineKeyboardButton(text=get_text(lang, "btn_adm_cancel_no"), callback_data=f"adm_cancel_no:{booking_id}"),
            ]
        ]
    )


def admin_masters_kb(lang: str, masters: list) -> InlineKeyboardMarkup:
    """List of masters: 'Alex · Barber Studio Center'."""
    rows = [
        [InlineKeyboardButton(
            text=f"{master['name']} · {master[f'branch_{lang}']}",
            callback_data=f"adm_master:{master['id']}",
        )]
        for master in masters
    ]
    rows.append([InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_days_off_kb(
    lang: str, master_id: int, days: List[date], closed: List[str], today: date
) -> InlineKeyboardMarkup:
    """Dates of a master. Closed days are marked with 🚫, tapping a date toggles it."""
    buttons = []
    for day in days:
        label = day_label(lang, day, today)
        if day.isoformat() in closed:
            label = "🚫 " + label
        buttons.append(InlineKeyboardButton(
            text=label, callback_data=f"adm_day:{master_id}:{day.isoformat()}"
        ))
    rows = split_rows(buttons, 2)
    rows.append([InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="adm:days_off")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
