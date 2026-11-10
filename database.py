"""Everything related to the SQLite database."""

from typing import Optional
from urllib.parse import quote_plus

import aiosqlite

from config import DB_PATH, DEFAULT_LANGUAGE, DEFAULT_WORK_END, DEFAULT_WORK_START

# SQL that creates all tables. "IF NOT EXISTS" makes it safe to run on every start.
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,          -- Telegram user id
    username    TEXT,
    language    TEXT,                         -- 'en' / 'uk', NULL = not chosen yet
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS branches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name_en     TEXT NOT NULL,
    name_uk     TEXT NOT NULL,
    address_en  TEXT NOT NULL,
    address_uk  TEXT NOT NULL,
    open_time   TEXT NOT NULL,                -- 'HH:MM'
    close_time  TEXT NOT NULL,                -- 'HH:MM'
    maps_url    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name_en     TEXT NOT NULL,
    name_uk     TEXT NOT NULL,
    price       INTEGER NOT NULL,             -- in UAH
    duration    INTEGER NOT NULL              -- in minutes
);

CREATE TABLE IF NOT EXISTS masters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id       INTEGER NOT NULL,
    name            TEXT NOT NULL,
    description_en  TEXT,
    description_uk  TEXT,
    photo_url       TEXT,
    work_start      TEXT NOT NULL,            -- 'HH:MM'
    work_end        TEXT NOT NULL,            -- 'HH:MM'
    is_active       INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (branch_id) REFERENCES branches (id)
);

-- Which master can do which service (many-to-many)
CREATE TABLE IF NOT EXISTS master_services (
    master_id   INTEGER NOT NULL,
    service_id  INTEGER NOT NULL,
    PRIMARY KEY (master_id, service_id),
    FOREIGN KEY (master_id) REFERENCES masters (id),
    FOREIGN KEY (service_id) REFERENCES services (id)
);

CREATE TABLE IF NOT EXISTS bookings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    branch_id      INTEGER NOT NULL,
    master_id      INTEGER NOT NULL,
    service_id     INTEGER NOT NULL,
    start_at       TEXT NOT NULL,             -- 'YYYY-MM-DD HH:MM', Kyiv time
    end_at         TEXT NOT NULL,             -- 'YYYY-MM-DD HH:MM', Kyiv time
    client_name    TEXT,
    client_phone   TEXT,
    status         TEXT NOT NULL DEFAULT 'active',  -- active / cancelled / completed
    -- 1 = reminder already sent (or not needed), 0 = still waiting
    reminder_24h_sent  INTEGER NOT NULL DEFAULT 0,
    reminder_2h_sent   INTEGER NOT NULL DEFAULT 0,
    confirmed      INTEGER NOT NULL DEFAULT 0,      -- 1 = client pressed "I'll come"
    -- Review after the visit
    review_at      TEXT,                            -- when to ask for a rating, Kyiv time
    review_sent    INTEGER NOT NULL DEFAULT 0,      -- 1 = rating request already sent
    rating         INTEGER,                         -- 1..5, NULL = not rated yet
    review_text    TEXT,                            -- what the client didn't like
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (branch_id) REFERENCES branches (id),
    FOREIGN KEY (master_id) REFERENCES masters (id),
    FOREIGN KEY (service_id) REFERENCES services (id)
);

-- Days when a master doesn't work (closed by an admin)
CREATE TABLE IF NOT EXISTS days_off (
    master_id   INTEGER NOT NULL,
    day         TEXT NOT NULL,                -- 'YYYY-MM-DD'
    PRIMARY KEY (master_id, day),
    FOREIGN KEY (master_id) REFERENCES masters (id)
);
"""


async def init_db() -> None:
    """Create tables and fill them with demo data on the first run."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()
    await migrate()
    await seed_demo_data()


async def migrate() -> None:
    """Update a database created by an older version of the bot.

    "CREATE TABLE IF NOT EXISTS" does not change an existing table,
    so new columns have to be added by hand with ALTER TABLE.
    """
    new_columns = {
        "reminder_24h_sent": "INTEGER NOT NULL DEFAULT 0",
        "reminder_2h_sent": "INTEGER NOT NULL DEFAULT 0",
        "confirmed": "INTEGER NOT NULL DEFAULT 0",
        "review_at": "TEXT",
        "review_sent": "INTEGER NOT NULL DEFAULT 0",
        "rating": "INTEGER",
        "review_text": "TEXT",
    }
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("PRAGMA table_info(bookings)")
        existing = [row[1] for row in await cursor.fetchall()]  # row[1] = column name

        for name, definition in new_columns.items():
            if name not in existing:
                await db.execute(f"ALTER TABLE bookings ADD COLUMN {name} {definition}")

        # Column from stage 1-2, replaced by the two columns above
        if "reminder_sent" in existing:
            await db.execute("ALTER TABLE bookings DROP COLUMN reminder_sent")

        await db.commit()


def _maps_link(address: str) -> str:
    """Build a Google Maps search link for an address."""
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(address)


async def seed_demo_data() -> None:
    """Insert demo branches, services and masters if the database is empty."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM branches")
        (count,) = await cursor.fetchone()
        if count > 0:
            return  # data already exists, nothing to do

        # --- Branches ---
        branches = [
            (
                "Barber Studio Center", "Barber Studio Центр",
                "22 Khreshchatyk St, Kyiv", "вул. Хрещатик, 22, Київ",
                "10:00", "20:00",
                _maps_link("Khreshchatyk St 22, Kyiv"),
            ),
            (
                "Barber Studio Podil", "Barber Studio Поділ",
                "15 Sahaidachnoho St, Kyiv", "вул. Сагайдачного, 15, Київ",
                "10:00", "20:00",
                _maps_link("Sahaidachnoho St 15, Kyiv"),
            ),
        ]
        await db.executemany(
            """INSERT INTO branches
               (name_en, name_uk, address_en, address_uk, open_time, close_time, maps_url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            branches,
        )

        # --- Services: (name_en, name_uk, price in UAH, duration in minutes) ---
        services = [
            ("Haircut", "Стрижка", 500, 60),
            ("Beard", "Борода", 300, 30),
            ("Haircut + Beard", "Стрижка + борода", 750, 90),
            ("Kids haircut", "Дитяча стрижка", 400, 45),
        ]
        await db.executemany(
            "INSERT INTO services (name_en, name_uk, price, duration) VALUES (?, ?, ?, ?)",
            services,
        )

        # --- Masters: (branch_id, name, description_en, description_uk, photo_url) ---
        # Photos are placeholder images. Replace with real photo links later.
        masters = [
            (
                1, "Alex",
                "Senior barber, 8 years of experience. Classic cuts and fades.",
                "Старший барбер, 8 років досвіду. Класичні стрижки та фейди.",
                "https://placehold.co/600x600/png?text=Alex",
            ),
            (
                1, "Max",
                "Beard specialist. Precise beard shaping and hot towel shave.",
                "Спеціаліст з бороди. Чітке оформлення бороди та гоління з гарячим рушником.",
                "https://placehold.co/600x600/png?text=Max",
            ),
            (
                2, "Dmytro",
                "Creative haircuts. Patient and friendly with kids.",
                "Креативні стрижки. Терплячий і привітний з дітьми.",
                "https://placehold.co/600x600/png?text=Dmytro",
            ),
        ]
        for branch_id, name, desc_en, desc_uk, photo in masters:
            await db.execute(
                """INSERT INTO masters
                   (branch_id, name, description_en, description_uk, photo_url,
                    work_start, work_end)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (branch_id, name, desc_en, desc_uk, photo,
                 DEFAULT_WORK_START, DEFAULT_WORK_END),
            )

        # --- Which master does which service: (master_id, service_id) ---
        # Service ids: 1 Haircut, 2 Beard, 3 Haircut + Beard, 4 Kids haircut
        master_services = [
            (1, 1), (1, 2), (1, 3), (1, 4),  # Alex does everything
            (2, 1), (2, 2), (2, 3),          # Max: no kids haircut
            (3, 1), (3, 3), (3, 4),          # Dmytro: no beard-only service
        ]
        await db.executemany(
            "INSERT INTO master_services (master_id, service_id) VALUES (?, ?)",
            master_services,
        )

        await db.commit()


# ---------- Small helpers for SELECT queries ----------
# Rows work like dicts: row["name_en"], row["price"], ...

async def fetch_one(sql: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
    """Run a SELECT and return the first row (or None)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        return await cursor.fetchone()


async def fetch_all(sql: str, params: tuple = ()) -> list:
    """Run a SELECT and return all rows as a list."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        return list(await cursor.fetchall())


# ---------- Users ----------

async def add_user(user_id: int, username: Optional[str]) -> None:
    """Save a new user, or update the username of an existing one."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (user_id, username) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET username = excluded.username""",
            (user_id, username),
        )
        await db.commit()


async def get_user_language(user_id: int) -> Optional[str]:
    """Return the user's language, or None if it was not chosen yet."""
    row = await fetch_one("SELECT language FROM users WHERE user_id = ?", (user_id,))
    return row["language"] if row else None


async def get_lang(user_id: int) -> str:
    """Same as above, but returns the default language instead of None."""
    return await get_user_language(user_id) or DEFAULT_LANGUAGE


async def set_user_language(user_id: int, language: str) -> None:
    """Save the chosen language (creates the user if needed)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (user_id, language) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET language = excluded.language""",
            (user_id, language),
        )
        await db.commit()


# ---------- Branches ----------

async def get_branches() -> list:
    """Return all branches."""
    return await fetch_all("SELECT * FROM branches ORDER BY id")


async def get_branch(branch_id: int) -> Optional[aiosqlite.Row]:
    return await fetch_one("SELECT * FROM branches WHERE id = ?", (branch_id,))


# ---------- Services ----------

async def get_services_for_branch(branch_id: int) -> list:
    """Services that at least one active master of this branch can do."""
    return await fetch_all(
        """SELECT DISTINCT s.*
           FROM services s
           JOIN master_services ms ON ms.service_id = s.id
           JOIN masters m ON m.id = ms.master_id
           WHERE m.branch_id = ? AND m.is_active = 1
           ORDER BY s.id""",
        (branch_id,),
    )


async def get_service(service_id: int) -> Optional[aiosqlite.Row]:
    return await fetch_one("SELECT * FROM services WHERE id = ?", (service_id,))


# ---------- Masters ----------

async def get_masters(branch_id: int, service_id: int) -> list:
    """Active masters of the branch who can do the service."""
    return await fetch_all(
        """SELECT m.*
           FROM masters m
           JOIN master_services ms ON ms.master_id = m.id
           WHERE m.branch_id = ? AND ms.service_id = ? AND m.is_active = 1
           ORDER BY m.id""",
        (branch_id, service_id),
    )


async def get_master(master_id: int) -> Optional[aiosqlite.Row]:
    return await fetch_one("SELECT * FROM masters WHERE id = ?", (master_id,))


# ---------- Bookings ----------

async def get_master_bookings_for_day(master_id: int, day: str) -> list:
    """Not cancelled bookings of a master on one day. day looks like '2026-11-10'."""
    return await fetch_all(
        """SELECT start_at, end_at FROM bookings
           WHERE master_id = ? AND status != 'cancelled' AND start_at LIKE ?""",
        (master_id, day + "%"),
    )


async def create_booking(
    user_id: int,
    branch_id: int,
    master_id: int,
    service_id: int,
    start_at: str,
    end_at: str,
    client_name: str,
) -> Optional[int]:
    """Save a booking and return its id.

    Returns None if the master is already busy at this time
    (for example, another client booked it a second earlier).
    """
    # isolation_level=None lets us control the transaction ourselves
    async with aiosqlite.connect(DB_PATH, isolation_level=None) as db:
        # BEGIN IMMEDIATE locks the database for writing, so two clients
        # can't check "is it free?" at the same moment and both get the slot
        await db.execute("BEGIN IMMEDIATE")

        # Is there any booking that overlaps the new time?
        # (dates are stored as 'YYYY-MM-DD HH:MM', so text comparison works)
        cursor = await db.execute(
            """SELECT id FROM bookings
               WHERE master_id = ? AND status != 'cancelled'
                 AND start_at < ? AND end_at > ?""",
            (master_id, end_at, start_at),
        )
        if await cursor.fetchone():
            await db.execute("ROLLBACK")
            return None

        cursor = await db.execute(
            """INSERT INTO bookings
               (user_id, branch_id, master_id, service_id, start_at, end_at, client_name)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, branch_id, master_id, service_id, start_at, end_at, client_name),
        )
        await db.execute("COMMIT")
        return cursor.lastrowid


async def get_booking(booking_id: int) -> Optional[aiosqlite.Row]:
    return await fetch_one("SELECT * FROM bookings WHERE id = ?", (booking_id,))


async def get_user_upcoming_bookings(user_id: int, now: str) -> list:
    """Active bookings of one client that haven't started yet, nearest first."""
    return await fetch_all(
        """SELECT * FROM bookings
           WHERE user_id = ? AND status = 'active' AND start_at > ?
           ORDER BY start_at""",
        (user_id, now),
    )


async def get_all_upcoming_bookings(now: str) -> list:
    """Active future bookings of all clients (used to restore reminders)."""
    return await fetch_all(
        "SELECT * FROM bookings WHERE status = 'active' AND start_at > ? ORDER BY start_at",
        (now,),
    )


async def cancel_booking(booking_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
        await db.commit()


async def confirm_visit(booking_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE bookings SET confirmed = 1 WHERE id = ?", (booking_id,))
        await db.commit()


async def mark_reminder_sent(booking_id: int, kind: str) -> None:
    """kind is '24h' or '2h'."""
    # A column name can't be passed as "?", so we build it from a fixed list only
    column = {"24h": "reminder_24h_sent", "2h": "reminder_2h_sent"}[kind]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE bookings SET {column} = 1 WHERE id = ?", (booking_id,))
        await db.commit()


# ---------- Admin: bookings of a day ----------

async def get_bookings_for_day(day: str) -> list:
    """All not-cancelled bookings of one day (all masters), by time.

    LEFT JOIN users adds the client's @username to every row.
    """
    return await fetch_all(
        """SELECT b.*, u.username
           FROM bookings b
           LEFT JOIN users u ON u.user_id = b.user_id
           WHERE b.start_at LIKE ? AND b.status != 'cancelled'
           ORDER BY b.start_at""",
        (day + "%",),
    )


async def complete_booking(booking_id: int, review_at: Optional[str]) -> None:
    """Mark a booking as done and remember when to ask the client for a rating.

    review_at=None means "don't ask for a rating".
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bookings SET status = 'completed', review_at = ? WHERE id = ?",
            (review_at, booking_id),
        )
        await db.commit()


# ---------- Reviews ----------

async def get_pending_review_requests() -> list:
    """Completed bookings whose rating request is not sent yet."""
    return await fetch_all(
        """SELECT * FROM bookings
           WHERE status = 'completed' AND review_sent = 0
             AND review_at IS NOT NULL AND rating IS NULL"""
    )


async def get_last_unrated_completed(user_id: int) -> Optional[aiosqlite.Row]:
    """The latest completed and not yet rated booking of a user (for /test_review)."""
    return await fetch_one(
        """SELECT * FROM bookings
           WHERE user_id = ? AND status = 'completed' AND rating IS NULL
           ORDER BY start_at DESC LIMIT 1""",
        (user_id,),
    )


async def mark_review_sent(booking_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE bookings SET review_sent = 1 WHERE id = ?", (booking_id,))
        await db.commit()


async def set_rating(booking_id: int, rating: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE bookings SET rating = ? WHERE id = ?", (rating, booking_id))
        await db.commit()


async def set_review_text(booking_id: int, text: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE bookings SET review_text = ? WHERE id = ?", (text, booking_id))
        await db.commit()


# ---------- Days off ----------

async def get_all_masters() -> list:
    """All active masters with the name of their branch."""
    return await fetch_all(
        """SELECT m.*, b.name_en AS branch_en, b.name_uk AS branch_uk
           FROM masters m JOIN branches b ON b.id = m.branch_id
           WHERE m.is_active = 1
           ORDER BY m.id"""
    )


async def get_days_off(master_id: int) -> list:
    """List of closed days of a master, e.g. ['2026-11-12', ...]."""
    rows = await fetch_all("SELECT day FROM days_off WHERE master_id = ?", (master_id,))
    return [row["day"] for row in rows]


async def is_day_off(master_id: int, day: str) -> bool:
    row = await fetch_one(
        "SELECT 1 FROM days_off WHERE master_id = ? AND day = ?", (master_id, day)
    )
    return row is not None


async def toggle_day_off(master_id: int, day: str) -> bool:
    """Close the day if it's open, open it if it's closed.

    Returns True if the day is closed now.
    """
    closed = await is_day_off(master_id, day)
    async with aiosqlite.connect(DB_PATH) as db:
        if closed:
            await db.execute(
                "DELETE FROM days_off WHERE master_id = ? AND day = ?", (master_id, day)
            )
        else:
            await db.execute(
                "INSERT INTO days_off (master_id, day) VALUES (?, ?)", (master_id, day)
            )
        await db.commit()
    return not closed


async def get_booking_counts(from_day: str) -> dict:
    """How many not-cancelled bookings each day has, starting from from_day.

    Returns e.g. {'2026-11-10': 2, '2026-11-12': 5}.
    substr(start_at, 1, 10) cuts '2026-11-10 14:30' down to '2026-11-10'.
    """
    rows = await fetch_all(
        """SELECT substr(start_at, 1, 10) AS day, COUNT(*) AS count
           FROM bookings
           WHERE status != 'cancelled' AND start_at >= ?
           GROUP BY day""",
        (from_day,),
    )
    return {row["day"]: row["count"] for row in rows}


async def get_active_bookings_from(from_day: str) -> list:
    """All active bookings from the start of from_day, with the client's @username."""
    return await fetch_all(
        """SELECT b.*, u.username
           FROM bookings b
           LEFT JOIN users u ON u.user_id = b.user_id
           WHERE b.status = 'active' AND b.start_at >= ?
           ORDER BY b.start_at""",
        (from_day,),
    )


async def get_bookings_to_auto_complete(ended_before: str) -> list:
    """Active bookings that ended before the given time (admin didn't mark them)."""
    return await fetch_all(
        "SELECT * FROM bookings WHERE status = 'active' AND end_at <= ? ORDER BY end_at",
        (ended_before,),
    )
