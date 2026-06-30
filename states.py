"""
states.py
تمام Stateهای FSM ربات اینجا تعریف می‌شوند تا در همه‌ی handlerها
قابل import و استفاده باشند.
"""

from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    waiting_custom_charge = State()
    waiting_charge_receipt = State()
    waiting_ticket_message = State()
    waiting_broadcast = State()
    waiting_config = State()
    waiting_discount_code = State()


class AdminStates(StatesGroup):
    waiting_custom_amount = State()
    waiting_new_discount = State()
    waiting_search_user = State()
