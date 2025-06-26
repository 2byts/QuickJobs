from aiogram.fsm.state import StatesGroup, State

class RegistrationStates(StatesGroup):
    awaiting_facebook_id = State()
    awaiting_two_step_key = State()
    awaiting_twofa_confirm = State()   # Needed for TOTP inline step
    awaiting_webmail = State()         # 👈 You forgot this one


# Import all handler modules
from . import (
    start_handler,
    registration_handler,
    balance_handler,
    accounts_handler,
    help_handler,
    admin_handler  
)