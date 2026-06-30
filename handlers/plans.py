"""
handlers/plans.py
نمایش دسته‌بندی سرویس‌ها (VIP / Gaming)، اعمال کد تخفیف، خرید سرویس،
و نمایش سرویس‌های خریداری‌شده کاربر.

نکته مهم: همین‌جا (در confirm_buy) بعد از یک خرید موفق، اگر این اولین خرید
کاربر باشد، db.complete_referral فراخوانی می‌شود تا اگر معرفی داشته،
مبلغ قفل‌شده‌ی معرفش آزاد شود.
"""

from datetime import datetime, timedelta

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

import database as db
import crypto
from states import UserStates
from config import PLANS, ADMIN_ID
from keyboards import (
    services_menu,
    vip_plans_keyboard,
    gaming_plans_keyboard,
    all_plans_discount_keyboard,
    buy_confirm_keyboard,
    insufficient_balance_keyboard,
    back_button,
    admin_purchase_notify_keyboard,
)

router = Router(name="plans")


@router.callback_query(F.data == "plans")
async def show_services(callback: types.CallbackQuery):
    await callback.message.edit_text("📦 دسته‌بندی سرویس‌ها:", reply_markup=services_menu())
    await callback.answer()


@router.callback_query(F.data == "plans_vip")
async def show_vip_plans(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    discount = data.get("discount_percent", 0)
    await callback.message.edit_text("👑 سرویس‌های VIP:", reply_markup=vip_plans_keyboard(discount))
    await callback.answer()


@router.callback_query(F.data == "plans_gaming")
async def show_gaming_plans(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    discount = data.get("discount_percent", 0)
    await callback.message.edit_text("🎮 سرورهای گیمینگ:", reply_markup=gaming_plans_keyboard(discount))
    await callback.answer()


@router.callback_query(F.data == "use_discount")
async def use_discount(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🎟 کد تخفیف خود را وارد کنید:")
    await state.set_state(UserStates.waiting_discount_code)
    await callback.answer()


@router.message(UserStates.waiting_discount_code)
async def check_discount(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    discount = db.get_discount(code)

    if discount is None or discount["uses"] <= 0:
        await message.answer(
            "❌ کد تخفیف نامعتبر یا تمام شده.",
            reply_markup=back_button("plans", "🔙 بازگشت"),
        )
        await state.clear()
        return

    await state.update_data(discount_code=code, discount_percent=discount["percent"])
    await message.answer(
        f"✅ کد تخفیف {discount['percent']}٪ اعمال شد!",
        reply_markup=all_plans_discount_keyboard(discount["percent"]),
    )
    await state.clear()
  # ---------------------------------------------------------------------------
# خرید سرویس
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith("buy_"))
async def buy_plan(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data.replace("buy_", "")
    plan = PLANS.get(plan_key)
    if plan is None:
        await callback.answer("❌ این پلن یافت نشد.", show_alert=True)
        return

    user = db.get_user(callback.from_user.id)
    if user is None:
        await callback.answer("ابتدا دستور /start را بزنید.", show_alert=True)
        return

    data = await state.get_data()
    discount = data.get("discount_percent", 0)
    final_price = int(plan["price"] * (1 - discount / 100))

    if user["wallet"] >= final_price:
        text = f"🛒 {plan['name']}\n💰 قیمت: {final_price:,} تومان"
        if discount:
            text += f" (تخفیف {discount}٪)"
        text += f"\n💵 موجودی شما: {user['wallet']:,} تومان\n\nآیا تأیید می‌کنید؟"
        await callback.message.edit_text(text, reply_markup=buy_confirm_keyboard(plan_key))
    else:
        needed = final_price - user["wallet"]
        await callback.message.edit_text(
            f"❌ موجودی کافی نیست!\n\n"
            f"💰 قیمت: {final_price:,} تومان\n"
            f"💵 موجودی: {user['wallet']:,} تومان\n"
            f"⚠️ کمبود: {needed:,} تومان",
            reply_markup=insufficient_balance_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_buy(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data.replace("confirm_", "")
    plan = PLANS.get(plan_key)
    if plan is None:
        await callback.answer("❌ این پلن یافت نشد.", show_alert=True)
        return

    user = db.get_user(callback.from_user.id)
    if user is None:
        await callback.answer("ابتدا دستور /start را بزنید.", show_alert=True)
        return

    data = await state.get_data()
    discount = data.get("discount_percent", 0)
    discount_code = data.get("discount_code", "")
    final_price = int(plan["price"] * (1 - discount / 100))

    previous_purchases = [
        tx for tx in db.get_transactions(user["id"], limit=1000) if tx["type"] == "purchase"
    ]
    is_first_purchase = len(previous_purchases) == 0

    success = db.deduct_from_wallet(user["id"], final_price, f"خرید {plan['name']}")
    if not success:
        await callback.message.edit_text(
            "❌ موجودی کافی نیست. ممکن است موجودی شما تغییر کرده باشد.",
            reply_markup=insufficient_balance_keyboard(),
        )
        await callback.answer()
        return

    if discount_code:
        db.use_discount(discount_code)

    if is_first_purchase:
        try:
            db.complete_referral(user["id"])
        except ValueError:
            pass

    expiry = ""
    if plan["days"] > 0:
        expiry = (datetime.now() + timedelta(days=plan["days"])).strftime("%Y-%m-%d")

    await state.update_data(pending_plan=plan_key, pending_expiry=expiry, pending_uid=str(callback.from_user.id))

    await callback.bot.send_message(
        ADMIN_ID,
        f"🛒 خرید جدید!\n\n"
        f"👤 {callback.from_user.full_name}\n"
        f"🆔 {callback.from_user.id}\n"
        f"📦 {plan['name']}\n"
        f"💰 {final_price:,} تومان",
        reply_markup=admin_purchase_notify_keyboard(str(callback.from_user.id)),
    )
    await callback.message.edit_text("✅ خرید موفق! سرویس شما بزودی ارسال می‌شود.")
    await callback.answer()


# ---------------------------------------------------------------------------
# سرویس‌های من
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "my_configs")
async def my_configs(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if user is None:
        await callback.answer("ابتدا دستور /start را بزنید.", show_alert=True)
        return

    configs = db.get_configs(user["id"])
    if not configs:
        text = "📱 شما هنوز سرویسی ندارید."
    else:
        text = "📱 سرویس‌های شما:\n\n"
        for i, cfg in enumerate(configs, 1):
            try:
                decrypted = crypto.decrypt_config(cfg["config"])
            except Exception:
                decrypted = "⚠️ خطا در رمزگشایی کانفیگ - با پشتیبانی تماس بگیرید."
            text += f"━━━━━━━━━━\n🔹 سرویس {i}\n📅 پلن: {cfg['plan']}\n"
            if cfg["expiry"]:
                text += f"⏰ انقضا: {cfg['expiry']}\n"
            text += f"📆 خرید: {cfg['created_at']}\n```{decrypted}```\n"

    await callback.message.edit_text(
        text, parse_mode="Markdown", reply_markup=back_button("plans", "🔙 بازگشت")
    )
    await callback.answer()
