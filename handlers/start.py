"""
handlers/start.py
دستور /start، بررسی عضویت اجباری در کانال‌ها، و پردازش لینک دعوت اختصاصی
(/start BVPNXXXXX).
"""

import logging

from aiogram import Router, F, types
from aiogram.filters import Command, CommandObject
from aiogram.enums import ChatMemberStatus

import database as db
from keyboards import join_channels_keyboard, main_menu
from config import REQUIRED_CHANNELS

router = Router(name="start")
logger = logging.getLogger(name)


async def check_membership(bot, user_id: int) -> list:
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(ch["id"], user_id)
            if member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED, ChatMemberStatus.BANNED):
                not_joined.append(ch)
        except Exception as e:
            logger.error(f"check_membership failed for channel {ch['id']}: {e}")
            not_joined.append(ch)
    return not_joined


def _ensure_user(telegram_id, full_name: str, referrer_code: str | None = None):
    """کاربر را اگر وجود نداشت می‌سازد؛ کد دعوت معتبر را هم پاس می‌دهد."""
    return db.create_user(telegram_id, full_name, referrer_invite_code=referrer_code)


def _welcome_text(first_name: str) -> str:
    return f"👋 به ربات بیزنس خوش آمدید {first_name}!\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:"


@router.message(Command("start"))
async def start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    not_joined = await check_membership(message.bot, user_id)

    referrer_code = command.args.strip() if command.args else None

    if not_joined:
        await message.answer(
            "⚠️ برای استفاده از ربات ابتدا در کانال‌های زیر عضو شوید:",
            reply_markup=join_channels_keyboard(not_joined),
        )
        _ensure_user(user_id, message.from_user.full_name, referrer_code)
        return

    _ensure_user(user_id, message.from_user.full_name, referrer_code)

    await message.answer(_welcome_text(message.from_user.first_name), reply_markup=main_menu())


@router.callback_query(F.data == "check_join")
async def check_join(callback: types.CallbackQuery):
    not_joined = await check_membership(callback.bot, callback.from_user.id)
    if not_joined:
        await callback.answer("❌ هنوز در همه کانال‌ها عضو نشدید!", show_alert=True)
        return

    _ensure_user(callback.from_user.id, callback.from_user.full_name)

    await callback.message.edit_text(
        _welcome_text(callback.from_user.first_name), reply_markup=main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 خوش آمدید!\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=main_menu(),
    )
    await callback.answer()
