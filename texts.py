"""All bot texts in one place, grouped by language."""

from datetime import date

from config import DEFAULT_LANGUAGE

# Short weekday names, Monday first (date.weekday() returns 0 for Monday)
WEEKDAYS = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "uk": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
}

TEXTS = {
    "en": {
        # Language selection
        "choose_language": "🌐 Choose your language / Оберіть мову:",
        "language_set": "✅ Language set: English",

        # Greeting and main menu
        "welcome": (
            "Hi! 👋\n"
            "Welcome to <b>Barber Studio</b>.\n\n"
            "Here you can book an appointment with our masters in a few taps.\n"
            "Choose an option from the menu below 👇"
        ),
        "menu_placeholder": "Choose an option",
        "use_menu": "Please use the menu buttons below 👇",

        # Main menu buttons
        "btn_book": "✂️ Book an appointment",
        "btn_my_bookings": "📋 My bookings",
        "btn_locations": "📍 Our locations",
        "btn_language": "🌐 Language",

        # Locations
        "locations_title": "📍 <b>Our locations</b>",
        "branch_card": "<b>{name}</b>\n📍 {address}\n🕒 {hours}",
        "branch_hours": "Every day {open}–{close}",
        "btn_open_maps": "🗺 Open in Google Maps",
        "no_branches": "No locations yet.",

        # Booking: steps
        "choose_branch": "🏠 <b>Step 1/5.</b> Choose a location:",
        "choose_service": "✂️ <b>Step 2/5.</b> Choose a service:",
        "service_button": "{name} · {price} UAH · {duration} min",
        "master_card": (
            "👤 <b>Step 3/5.</b> Choose a master ({counter})\n\n"
            "<b>{name}</b>\n{description}"
        ),
        "btn_choose_master": "✅ Choose {name}",
        "no_masters": "😔 No masters available for this service. Please choose another one.",
        "choose_date": "📅 <b>Step 4/5.</b> Choose a date:",
        "no_dates": "😔 {name} has no free time in the next 7 days. Please choose another master.",
        "choose_time": "🕒 <b>Step 5/5.</b> Free time on {date}:",
        "no_times": "😔 No free time left on this day. Please choose another date.",
        "today": "Today",
        "tomorrow": "Tomorrow",

        # Booking: confirmation and result
        "booking_summary": (
            "🏠 {branch}\n"
            "📍 {address}\n"
            "✂️ {service}\n"
            "💰 {price} UAH · ⏱ {duration} min\n"
            "👤 Master: {master}\n"
            "📅 {date} at {time}"
        ),
        "confirm_booking": "Please check your booking:\n\n{summary}",
        "booking_done": "🎉 <b>You're booked!</b>\n\n{summary}\n\nSee you soon!",
        "booking_cancelled": "❌ Booking cancelled. Press ✂️ Book an appointment to start again.",
        "slot_taken": "😔 Sorry, this time was just taken. Please choose another one.",
        "button_outdated": "This button is outdated. Please use the menu.",

        # Booking: buttons
        "btn_confirm": "✅ Confirm",
        "btn_back": "⬅️ Back",
        "btn_cancel": "❌ Cancel",

        # My bookings
        "my_bookings_title": "📋 <b>Your upcoming bookings</b>",
        "no_bookings": "You have no upcoming bookings.\nPress ✂️ Book an appointment to make one.",
        "booking_item": "📌 <b>Booking #{id}</b>\n\n{summary}",
        "visit_confirmed_mark": "✅ You confirmed your visit",
        "btn_cancel_booking": "❌ Cancel booking",
        "btn_cancel_yes": "✅ Yes, cancel it",
        "btn_cancel_no": "↩️ No, keep it",
        "booking_cancelled_mark": "❌ <b>Booking cancelled.</b>",
        "booking_not_active": "This booking is no longer active.",

        # Reminders
        "reminder_24h": "⏰ <b>Reminder about your visit</b>\n\n{summary}\n\nWill you come?",
        "reminder_2h": "⏰ <b>Your visit is coming up soon!</b>\n\n{summary}\n\nWill you come?",
        "btn_will_come": "✅ I'll come",
        "btn_reminder_cancel": "❌ Cancel",
        "visit_confirmed": "✅ <b>Great, see you!</b>",

        # Review after the visit
        "review_request": (
            "⭐ <b>How was your visit?</b>\n\n{summary}\n\nPlease rate it from 1 to 5:"
        ),
        "review_your_rating": "Your rating: {stars}",
        "review_thanks_good": (
            "🙏 Thank you! We'd be really grateful if you left a review on Google Maps:"
        ),
        "btn_leave_review": "📍 Leave a review on Google Maps",
        "review_ask_text": (
            "😔 We're sorry. Please write what you didn't like - "
            "we'll pass it to the manager."
        ),
        "review_thanks_bad": "🙏 Thank you for the feedback! The manager will read it.",
        "review_already": "You have already rated this visit.",

        # Admin notifications
        "admin_new_booking": "🆕 <b>New booking #{id}</b>\n\n🙋 Client: {client}\n\n{summary}",
        "admin_booking_cancelled": (
            "❌ <b>Booking #{id} cancelled by the client</b>\n\n🙋 Client: {client}\n\n{summary}"
        ),
        "admin_feedback": (
            "⚠️ <b>Feedback on booking #{id}</b> - {stars}\n\n"
            "🙋 Client: {client}\n\n{summary}\n\n💬 {feedback}"
        ),

        # Admin panel
        "admin_menu": "🔐 <b>Admin panel</b>\nChoose an action:",
        "btn_adm_today": "📅 Today",
        "btn_adm_tomorrow": "📅 Tomorrow",
        "btn_adm_days_off": "🚫 Days off",
        "btn_adm_pick_date": "📆 Choose a date",
        "btn_adm_all": "📋 All upcoming",
        "adm_pick_date": "📆 <b>Choose a date</b>\nThe number shows how many bookings there are.",
        "adm_all_header": "📋 <b>All upcoming bookings: {count}</b>",
        "adm_all_empty": "📋 No upcoming bookings.",
        "adm_all_line": "<b>#{id}</b> {start}–{end} · {master} · {service} · {client}",
        "adm_all_hint": "To mark as done or cancel, open the day: 📆 Choose a date.",
        "adm_day_header": "📅 <b>{day}</b> - bookings: {count}",
        "adm_no_bookings_day": "📅 <b>{day}</b> - no bookings.",
        "adm_booking_card": (
            "📌 <b>#{id}</b> · {start}–{end}\n"
            "👤 Master: {master}\n"
            "✂️ {service} · {price} UAH\n"
            "🏠 {branch}\n"
            "🙋 {client}"
        ),
        "adm_mark_confirmed": "👍 Client confirmed the visit",
        "adm_mark_done": "✔️ <b>Done</b>",
        "adm_mark_rating": "⭐ Rating: {stars}",
        "adm_mark_cancelled": "❌ <b>Cancelled by admin</b>",
        "btn_adm_done": "✔️ Done",
        "btn_adm_cancel": "❌ Cancel",
        "btn_adm_cancel_yes": "✅ Yes, cancel",
        "btn_adm_cancel_no": "↩️ No",
        "adm_not_today": "You can mark as done only today's or past visits.",
        "adm_not_active": "This booking is no longer active.",
        "client_cancelled_by_admin": (
            "😔 <b>Your booking #{id} was cancelled by the barbershop.</b>\n\n"
            "{summary}\n\nPlease choose another time: ✂️ Book an appointment."
        ),
        "adm_choose_master": "🚫 <b>Days off</b>\nChoose a master:",
        "adm_choose_day_off": "🚫 <b>{master}</b>\nTap a date to close or open it.\n🚫 = day off",
        "adm_day_closed": "Day closed.",
        "adm_day_opened": "Day opened.",
        "adm_no_review_test": (
            "You have no completed unrated bookings. "
            "Mark your own booking as ✔️ Done in /admin first."
        ),
        "adm_day_closed_warning": (
            "Day closed. ⚠️ There are {count} active bookings on this day - "
            "they were NOT cancelled. Cancel them in the bookings list if needed."
        ),

        # Bot commands (shown in the Telegram menu)
        "cmd_start": "Main menu",
        "cmd_language": "Change language",
    },
    "uk": {
        # Language selection
        "choose_language": "🌐 Choose your language / Оберіть мову:",
        "language_set": "✅ Мову змінено: Українська",

        # Greeting and main menu
        "welcome": (
            "Привіт! 👋\n"
            "Ласкаво просимо до <b>Barber Studio</b>.\n\n"
            "Тут можна записатися до наших майстрів за кілька натискань.\n"
            "Оберіть пункт меню нижче 👇"
        ),
        "menu_placeholder": "Оберіть пункт меню",
        "use_menu": "Будь ласка, скористайтеся кнопками меню нижче 👇",

        # Main menu buttons
        "btn_book": "✂️ Записатися",
        "btn_my_bookings": "📋 Мої записи",
        "btn_locations": "📍 Наші філії",
        "btn_language": "🌐 Мова",

        # Locations
        "locations_title": "📍 <b>Наші філії</b>",
        "branch_card": "<b>{name}</b>\n📍 {address}\n🕒 {hours}",
        "branch_hours": "Щодня {open}–{close}",
        "btn_open_maps": "🗺 Відкрити в Google Maps",
        "no_branches": "Філій поки немає.",

        # Booking: steps
        "choose_branch": "🏠 <b>Крок 1/5.</b> Оберіть філію:",
        "choose_service": "✂️ <b>Крок 2/5.</b> Оберіть послугу:",
        "service_button": "{name} · {price} грн · {duration} хв",
        "master_card": (
            "👤 <b>Крок 3/5.</b> Оберіть майстра ({counter})\n\n"
            "<b>{name}</b>\n{description}"
        ),
        "btn_choose_master": "✅ Обрати: {name}",
        "no_masters": "😔 Немає майстрів для цієї послуги. Оберіть іншу.",
        "choose_date": "📅 <b>Крок 4/5.</b> Оберіть дату:",
        "no_dates": "😔 У майстра {name} немає вільного часу найближчі 7 днів. Оберіть іншого майстра.",
        "choose_time": "🕒 <b>Крок 5/5.</b> Вільний час на {date}:",
        "no_times": "😔 На цей день вільного часу вже немає. Оберіть іншу дату.",
        "today": "Сьогодні",
        "tomorrow": "Завтра",

        # Booking: confirmation and result
        "booking_summary": (
            "🏠 {branch}\n"
            "📍 {address}\n"
            "✂️ {service}\n"
            "💰 {price} грн · ⏱ {duration} хв\n"
            "👤 Майстер: {master}\n"
            "📅 {date} о {time}"
        ),
        "confirm_booking": "Перевірте ваш запис:\n\n{summary}",
        "booking_done": "🎉 <b>Ви записані!</b>\n\n{summary}\n\nЧекаємо на вас!",
        "booking_cancelled": "❌ Запис скасовано. Натисніть ✂️ Записатися, щоб почати знову.",
        "slot_taken": "😔 Вибачте, цей час щойно зайняли. Оберіть інший.",
        "button_outdated": "Ця кнопка застаріла. Скористайтеся меню.",

        # Booking: buttons
        "btn_confirm": "✅ Підтвердити",
        "btn_back": "⬅️ Назад",
        "btn_cancel": "❌ Скасувати",

        # My bookings
        "my_bookings_title": "📋 <b>Ваші майбутні записи</b>",
        "no_bookings": "У вас немає майбутніх записів.\nНатисніть ✂️ Записатися, щоб записатися.",
        "booking_item": "📌 <b>Запис #{id}</b>\n\n{summary}",
        "visit_confirmed_mark": "✅ Ви підтвердили візит",
        "btn_cancel_booking": "❌ Скасувати запис",
        "btn_cancel_yes": "✅ Так, скасувати",
        "btn_cancel_no": "↩️ Ні, залишити",
        "booking_cancelled_mark": "❌ <b>Запис скасовано.</b>",
        "booking_not_active": "Цей запис уже не активний.",

        # Reminders
        "reminder_24h": "⏰ <b>Нагадування про візит</b>\n\n{summary}\n\nВи прийдете?",
        "reminder_2h": "⏰ <b>Ваш візит уже скоро!</b>\n\n{summary}\n\nВи прийдете?",
        "btn_will_come": "✅ Прийду",
        "btn_reminder_cancel": "❌ Скасувати",
        "visit_confirmed": "✅ <b>Чудово, чекаємо на вас!</b>",

        # Review after the visit
        "review_request": (
            "⭐ <b>Як пройшов ваш візит?</b>\n\n{summary}\n\nОцініть, будь ласка, від 1 до 5:"
        ),
        "review_your_rating": "Ваша оцінка: {stars}",
        "review_thanks_good": (
            "🙏 Дякуємо! Будемо дуже вдячні, якщо ви залишите відгук у Google Maps:"
        ),
        "btn_leave_review": "📍 Залишити відгук у Google Maps",
        "review_ask_text": (
            "😔 Нам дуже шкода. Напишіть, будь ласка, що вам не сподобалося - "
            "ми передамо це менеджеру."
        ),
        "review_thanks_bad": "🙏 Дякуємо за відгук! Менеджер обов'язково його прочитає.",
        "review_already": "Ви вже оцінили цей візит.",

        # Admin notifications
        "admin_new_booking": "🆕 <b>Новий запис #{id}</b>\n\n🙋 Клієнт: {client}\n\n{summary}",
        "admin_booking_cancelled": (
            "❌ <b>Клієнт скасував запис #{id}</b>\n\n🙋 Клієнт: {client}\n\n{summary}"
        ),
        "admin_feedback": (
            "⚠️ <b>Відгук на запис #{id}</b> - {stars}\n\n"
            "🙋 Клієнт: {client}\n\n{summary}\n\n💬 {feedback}"
        ),

        # Admin panel
        "admin_menu": "🔐 <b>Панель адміністратора</b>\nОберіть дію:",
        "btn_adm_today": "📅 Сьогодні",
        "btn_adm_tomorrow": "📅 Завтра",
        "btn_adm_days_off": "🚫 Вихідні",
        "btn_adm_pick_date": "📆 Обрати дату",
        "btn_adm_all": "📋 Усі записи",
        "adm_pick_date": "📆 <b>Оберіть дату</b>\nЧисло показує, скільки на цей день записів.",
        "adm_all_header": "📋 <b>Усі майбутні записи: {count}</b>",
        "adm_all_empty": "📋 Майбутніх записів немає.",
        "adm_all_line": "<b>#{id}</b> {start}–{end} · {master} · {service} · {client}",
        "adm_all_hint": "Щоб позначити виконаним або скасувати, відкрийте день: 📆 Обрати дату.",
        "adm_day_header": "📅 <b>{day}</b> - записів: {count}",
        "adm_no_bookings_day": "📅 <b>{day}</b> - записів немає.",
        "adm_booking_card": (
            "📌 <b>#{id}</b> · {start}–{end}\n"
            "👤 Майстер: {master}\n"
            "✂️ {service} · {price} грн\n"
            "🏠 {branch}\n"
            "🙋 {client}"
        ),
        "adm_mark_confirmed": "👍 Клієнт підтвердив візит",
        "adm_mark_done": "✔️ <b>Виконано</b>",
        "adm_mark_rating": "⭐ Оцінка: {stars}",
        "adm_mark_cancelled": "❌ <b>Скасовано адміністратором</b>",
        "btn_adm_done": "✔️ Виконано",
        "btn_adm_cancel": "❌ Скасувати",
        "btn_adm_cancel_yes": "✅ Так, скасувати",
        "btn_adm_cancel_no": "↩️ Ні",
        "adm_not_today": "Позначити виконаним можна лише сьогоднішні або минулі візити.",
        "adm_not_active": "Цей запис уже не активний.",
        "client_cancelled_by_admin": (
            "😔 <b>Ваш запис #{id} скасовано барбершопом.</b>\n\n"
            "{summary}\n\nОберіть, будь ласка, інший час: ✂️ Записатися."
        ),
        "adm_choose_master": "🚫 <b>Вихідні</b>\nОберіть майстра:",
        "adm_choose_day_off": "🚫 <b>{master}</b>\nНатисніть на дату, щоб закрити або відкрити її.\n🚫 = вихідний",
        "adm_day_closed": "День закрито.",
        "adm_day_opened": "День відкрито.",
        "adm_no_review_test": (
            "У вас немає виконаних записів без оцінки. "
            "Спочатку позначте свій запис як ✔️ Виконано в /admin."
        ),
        "adm_day_closed_warning": (
            "День закрито. ⚠️ На цей день є активних записів: {count} - "
            "їх НЕ скасовано. За потреби скасуйте їх у списку записів."
        ),

        # Bot commands (shown in the Telegram menu)
        "cmd_start": "Головне меню",
        "cmd_language": "Змінити мову",
    },
}


def get_text(lang: str, key: str, **kwargs) -> str:
    """Return the text for the given language.

    If the language is unknown, the default language is used.
    kwargs are inserted into the text, e.g. get_text("en", "branch_card", name="...").
    """
    texts = TEXTS.get(lang, TEXTS[DEFAULT_LANGUAGE])
    text = texts.get(key, TEXTS[DEFAULT_LANGUAGE][key])
    return text.format(**kwargs) if kwargs else text


def all_texts(key: str) -> list:
    """Return this text in every language.

    Useful for reply buttons: the user may press the button in any language,
    so the handler must react to all variants.
    """
    return [texts[key] for texts in TEXTS.values()]


def stars(rating: int) -> str:
    """3 -> '⭐⭐⭐'."""
    return "⭐" * rating


def format_date(lang: str, day: date) -> str:
    """date(2026, 11, 10) -> 'Tue, 10.11'."""
    weekday = WEEKDAYS.get(lang, WEEKDAYS[DEFAULT_LANGUAGE])[day.weekday()]
    return f"{weekday}, {day.strftime('%d.%m')}"
