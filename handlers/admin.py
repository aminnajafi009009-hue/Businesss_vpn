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
  
# ---------------------------------------------------------------------------
# 📤 ارسال کانفیگ
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "admin_send_config")
async def admin_send_config_info(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    await callback.message.edit_text(
        "📤 برای ارسال کانفیگ، از بخش «جستجوی حرفه‌ای» کاربر را پیدا کنید "
        "و دکمه «ارسال کانفیگ» را بزنید (یا روی پیام اطلاع‌رسانی خرید جدید همین دکمه هست).",
        reply_markup=admin_back_button(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sendconfig_"))
async def send_config_start(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    uid = callback.data.replace("sendconfig_", "")
    await state.update_data(config_target=uid)
    await state.set_state(AdminStates.waiting_config_text)
    await callback.message.answer(
        f"📤 کانفیگ برای کاربر {uid}:\n\n"
        f"خط اول را نام پلن و بقیه خطوط را متن کانفیگ بنویسید. مثال:\n\n"
        f"VIP 50 گیگ\nvless://....."
    )
    await callback.answer()


@router.message(AdminStates.waiting_config_text)
async def send_config_apply(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ لطفاً متن کانفیگ را ارسال کنید.")
        return

    data = await state.get_data()
    uid = data.get("config_target")
    user = db.get_user(uid)
    if user is None:
        await message.answer("❌ کاربر یافت نشد.")
        await state.clear()
        return

    lines = message.text.split("\n", 1)
    plan_name = lines[0].strip()
    config_text = lines[1].strip() if len(lines) > 1 else lines[0].strip()

    encrypted = crypto.encrypt_config(config_text)
    db.add_config(user["id"], plan_name, encrypted, expiry=None)

    await message.answer(f"✅ کانفیگ برای کاربر {uid} ثبت و ارسال شد.")
    try:
        await message.bot.send_message(
            int(uid),
            f"📦 سرویس شما آماده شد!\n\n📅 پلن: {plan_name}\n\n"
            f"برای مشاهده کانفیگ به «📦 سرویس‌ها → 📱 سرویس‌های من» مراجعه کنید.",
        )
    except Exception:
        pass
    await state.clear()


# ---------------------------------------------------------------------------
# 🎟 مدیریت تخفیف
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "admin_discount")
async def admin_discount_list(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    discounts = db.get_all_discounts()
    if not discounts:
        text = "🎟 هیچ کد تخفیفی ثبت نشده.\n\n"
    else:
        text = "🎟 کدهای تخفیف فعال:\n\n"
        for d in discounts:
            text += f"• {d['code']} | {d['percent']}٪ | باقی‌مانده: {d['uses']}\n"
        text += "\n"

    await callback.message.edit_text(text, reply_markup=admin_discount_menu())
    await callback.answer()


@router.callback_query(F.data == "new_discount")
async def new_discount_start(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    await callback.message.edit_text(
        "🎟 اطلاعات کد تخفیف را به این شکل ارسال کنید:\n\n"
        "CODE PERCENT USES\n\nمثال:\nSUMMER20 20 50",
        reply_markup=admin_back_button(),
    )
    await state.set_state(AdminStates.waiting_new_discount)
    await callback.answer()


@router.message(AdminStates.waiting_new_discount)
async def new_discount_apply(message: types.Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("❌ فرمت اشتباه است. مثال صحیح:\nSUMMER20 20 50")
        return

    code, percent, uses = parts[0], int(parts[1]), int(parts[2])
    try:
        db.create_discount(code, percent, uses)
        await message.answer(f"✅ کد تخفیف {code.upper()} با {percent}٪ و {uses} بار استفاده ساخته شد.")
    except Exception:
        await message.answer("❌ این کد قبلاً ثبت شده.")
    await state.clear()

# ---------------------------------------------------------------------------
# 👥 مدیریت دعوت‌ها
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "admin_referrals")
async def admin_referrals(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    users = db.get_all_users()
    top = sorted(users, key=lambda u: u["successful_invites"], reverse=True)[:10]

    if not top or top[0]["successful_invites"] == 0:
        text = "👥 هنوز هیچ دعوت موفقی ثبت نشده."
    else:
        text = "👥 برترین معرف‌ها:\n\n"
        for i, u in enumerate(top, 1):
            if u["successful_invites"] == 0:
                break
            text += (
                f"{i}. {u['name']} | دعوت: {u['invited_count']} | "
                f"موفق: {u['successful_invites']} | در انتظار: {u['locked_wallet']:,} تومان\n"
            )

    await callback.message.edit_text(text, reply_markup=admin_back_button())
    await callback.answer()


# ---------------------------------------------------------------------------
# 📢 پیام همگانی
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    await callback.message.edit_text(
        "📢 پیامی که می‌خواهید برای همه کاربران ارسال شود را بنویسید:",
        reply_markup=admin_back_button(),
    )
    await state.set_state(UserStates.waiting_broadcast)
    await callback.answer()


@router.message(UserStates.waiting_broadcast, F.from_user.id == ADMIN_ID)
async def admin_broadcast_send(message: types.Message, state: FSMContext):
    users = db.get_all_users()
    sent, failed = 0, 0

    status_msg = await message.answer(f"📢 در حال ارسال به {len(users)} کاربر...")

    for u in users:
        try:
            await message.bot.copy_message(int(u["telegram_id"]), message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(f"✅ ارسال شد به {sent} نفر. ناموفق: {failed} نفر.")
    await state.clear()


# ---------------------------------------------------------------------------
# 💾 بکاپ
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "admin_backup")
async def admin_backup(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    try:
        backup_file = FSInputFile(DATABASE_PATH)
        await callback.message.answer_document(backup_file, caption="💾 بکاپ دیتابیس")
    except Exception:
        await callback.message.answer("❌ خطا در ساخت بکاپ.")
    await callback.answer()
