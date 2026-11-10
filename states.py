"""FSM states (steps of multi-step dialogs).

FSM = Finite State Machine. The bot remembers on which step each user is,
so it knows what a button press means right now.
"""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Steps of the booking process, in order."""

    choosing_branch = State()
    choosing_service = State()
    choosing_master = State()
    choosing_date = State()
    choosing_time = State()
    confirming = State()


class ReviewStates(StatesGroup):
    """Client rated 1-3 ⭐ and the bot waits for a text about what went wrong."""

    waiting_text = State()
