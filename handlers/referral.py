"""
handlers/referral.py
نمایش لینک دعوت اختصاصی، کد اختصاصی، و آمار دعوت دوستان
(تعداد دعوت، دعوت‌های موفق، مبلغ آزاد شده، مبلغ در انتظار).
"""

from aiogram import Router, F, types

import database as db
from config import BOT_USERNAME
from keyboards import referral_menu

router = Router(name="referral")


@router.callback_query(F.data == "referral")
async def referral(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if user is None:
        await callback.answer("ابتدا دستور /start را بزنید.", show_alert=True)
        return

    stats = db.get_referral_stats(user["id"])
    invite_link = f"https://t.me/{BOT_USERNAME}?start={stats['invite_code']}"

    text = (
        f"👥 معرفی دوستان\n\n"
        f"🔗 لینک اختصاصی:\n{invite_link}\n\n"
        f"🔑 کد اختصاصی: {stats['invite_code']}\n\n"
        f"👤 تعداد دعوت: {stats['invited_count']}\n"
        f"✅ دعوت‌های موفق: {stats['successful_invites']}\n"
        f"🔓 مبلغ آزاد شده: {stats['released_amount']:,} تومان\n"
        f"🔒 مبلغ در انتظار: {user['locked_wallet']:,} تومان\n\n"
        f"ℹ️ به‌ازای هر دوستی که با لینک شما عضو شود و اولین خریدش را انجام دهد، "
        f"مبلغی به‌صورت خودکار به کیف پول شما آزاد می‌شود."
    )
    await callback.message.edit_text(text, reply_markup=referral_menu())
    await callback.answer()
