"""
handlers/admin.py
پنل کامل ادمین: آمار، جستجوی حرفه‌ای، شارژ کیف پول، ارسال کانفیگ،
مدیریت تخفیف، مدیریت دعوت‌ها، پیام همگانی، بکاپ.

تمام handlerهای این فایل فقط برای ADMIN_ID فعال هستند.
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

import database as db
import crypto
from states import AdminStates, UserStates
from config import ADMIN_ID, DATABASE_PATH, PLANS
from keyboards import (
    admin_panel_menu,
    admin_back_button,
    admin_discount_menu,
    admin_user_actions_keyboard,
)

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(Command("admin"))
async def admin_entry(message: types.Message):
    if not _is_admin(message.from_user.id):
        return  # کاربر عادی هیچ پاسخی نمی‌گیرد (نه حتی پیام خطا) - امنیتی
    await message.answer("👨‍💻 پنل مدیریت:", reply_markup=admin_panel_menu())


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("👨‍💻 پنل مدیریت:", reply_markup=admin_panel_menu())
    await callback.answer()


# ---------------------------------------------------------------------------
# 📊 آمار
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    text = (
        f"📊 آمار ربات\n\n"
        f"💰 فروش امروز: {db.sales_since(1):,} تومان\n"
        f"💰 فروش هفته: {db.sales_since(7):,} تومان\n"
        f"💰 فروش ماه: {db.sales_since(30):,} تومان\n"
        f"💰 کل فروش: {db.total_sales():,} تومان\n\n"
        f"👥 تعداد کاربران: {db.count_users()}\n"
        f"🟢 کاربران فعال (۳۰ روز اخیر): {db.count_active_users(30)}"
    )
    await callback.message.edit_text(text, reply_markup=admin_back_button())
    await callback.answer()


# ---------------------------------------------------------------------------
# 🔍 جستجوی حرفه‌ای
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "admin_search")
async def admin_search_start(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    await callback.message.edit_text(
        "🔍 آیدی عددی یا کد دعوت کاربر را ارسال کنید:", reply_markup=admin_back_button()
    )
    await state.set_state(AdminStates.waiting_search_user)
    await callback.answer()


@router.message(AdminStates.waiting_search_user)
async def admin_search_result(message: types.Message, state: FSMContext):
    query = message.text.strip()

    user = db.get_user(query) if query.isdigit() else db.get_user_by_invite_code(query)
    if user is None:
        await message.answer("❌ کاربری با این مشخصات یافت نشد.", reply_markup=admin_back_button())
        return

    stats = db.get_referral_stats(user["id"])
    text = (
        f"👤 {user['name']}\n"
        f"🆔 {user['telegram_id']}\n\n"
        f"💰 کیف پول آزاد: {user['wallet']:,} تومان\n"
        f"🔒 کیف پول مسدود: {user['locked_wallet']:,} تومان\n"
        f"🛒 کل خرید: {user['total_purchase']:,} تومان\n"
        f"📅 عضویت: {user['joined']}\n\n"
        f"🔗 کد دعوت: {user['invite_code']}\n"
        f"👥 دعوت: {stats['invited_count']} | موفق: {stats['successful_invites']}"
    )
    await message.answer(text, reply_markup=admin_user_actions_keyboard(user["telegram_id"]))
    await state.clear()
  # ---------------------------------------------------------------------------
# 💳 شارژ کیف پول (تأیید/رد رسید + شارژ دستی)
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "admin_charge_wallet")
async def admin_charge_wallet_info(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    await callback.message.edit_text(
        "💳 برای شارژ دستی کیف پول، ابتدا از بخش «جستجوی حرفه‌ای» کاربر را پیدا کنید "
        "و دکمه «شارژ دستی» را بزنید.\n\n"
        "رسیدهای ارسالی کاربران هم به‌صورت خودکار با دکمه تأیید/رد برای شما ارسال می‌شوند.",
        reply_markup=admin_back_button(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("approve_"))
async def approve_charge(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    _, uid, amount_str = callback.data.split("_")
    amount = int(amount_str)

    user = db.get_user(uid)
    if user is None:
        await callback.answer("❌ کاربر یافت نشد.", show_alert=True)
        return

    db.add_to_wallet(user["id"], amount, "شارژ کیف پول (تأیید رسید)")
    await callback.message.edit_text(callback.message.text + "\n\n✅ تأیید و شارژ شد.")
    try:
        await callback.bot.send_message(int(uid), f"✅ شارژ {amount:,} تومانی شما تأیید شد.")
    except Exception:
        pass
    await callback.answer("✅ شارژ شد.")


@router.callback_query(F.data.startswith("reject_"))
async def reject_charge(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    uid = callback.data.replace("reject_", "")
    await callback.message.edit_text(callback.message.text + "\n\n❌ رد شد.")
    try:
        await callback.bot.send_message(int(uid), "❌ متأسفانه رسید شما تأیید نشد. با پشتیبانی تماس بگیرید.")
    except Exception:
        pass
    await callback.answer("❌ رد شد.")


@router.callback_query(F.data.startswith("custom_"))
async def custom_charge_start(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    uid = callback.data.replace("custom_", "")
    await state.update_data(charge_target=uid)
    await state.set_state(AdminStates.waiting_custom_amount)
    await callback.message.answer(f"💵 مبلغ شارژ برای کاربر {uid} را به تومان ارسال کنید:")
    await callback.answer()


@router.message(AdminStates.waiting_custom_amount)
async def custom_charge_apply(message: types.Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("❌ فقط عدد ارسال کنید.")
        return

    data = await state.get_data()
    uid = data.get("charge_target")
    amount = int(message.text)

    user = db.get_user(uid)
    if user is None:
        await message.answer("❌ کاربر یافت نشد.")
        await state.clear()
        return

    db.add_to_wallet(user["id"], amount, "شارژ دستی توسط ادمین")
    await message.answer(f"✅ {amount:,} تومان به کیف پول کاربر {uid} اضافه شد.")
    try:
        await message.bot.send_message(int(uid), f"✅ کیف پول شما {amount:,} تومان شارژ شد.")
    except Exception:
        pass
    await state.clear()
  
