"""
handlers/wallet.py
نمایش کیف پول (موجودی آزاد / موجودی در انتظار)، تاریخچه تراکنش‌ها،
و فرایند شارژ کیف پول (انتخاب مبلغ یا مبلغ دلخواه + ارسال رسید).
"""

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

import database as db
from states import UserStates
from config import ADMIN_ID, CARD_NUMBER, CARD_HOLDER
from keyboards import (
    wallet_menu,
    charge_amount_keyboard,
    back_button,
    admin_charge_approval_keyboard,
)

router = Router(name="wallet")


def _get_user_row(telegram_id):
    """کاربر را برمی‌گرداند؛ اگر هنوز ساخته نشده، می‌سازد (محافظتی)."""
    user = db.get_user(telegram_id)
    if user is None:
        return None
    return user


@router.callback_query(F.data == "wallet")
async def wallet_overview(callback: types.CallbackQuery):
    user = _get_user_row(callback.from_user.id)
    if user is None:
        await callback.answer("ابتدا دستور /start را بزنید.", show_alert=True)
        return

    text = (
        f"💰 کیف پول شما\n\n"
        f"💰 موجودی قابل استفاده: {user['wallet']:,} تومان\n"
        f"🔒 موجودی در انتظار: {user['locked_wallet']:,} تومان\n\n"
        f"ℹ️ موجودی در انتظار، پس از اولین خرید فردی که با لینک شما عضو شده، "
        f"به‌صورت خودکار آزاد می‌شود."
    )
    await callback.message.edit_text(text, reply_markup=wallet_menu())
    await callback.answer()


@router.callback_query(F.data == "wallet_free")
async def wallet_free(callback: types.CallbackQuery):
    user = _get_user_row(callback.from_user.id)
    if user is None:
        await callback.answer("ابتدا دستور /start را بزنید.", show_alert=True)
        return
    text = f"💰 موجودی قابل استفاده شما\n\n{user['wallet']:,} تومان\n\nاین مبلغ را می‌توانید برای خرید سرویس استفاده کنید."
    await callback.message.edit_text(text, reply_markup=back_button("profile", "🔙 بازگشت"))
    await callback.answer()


@router.callback_query(F.data == "wallet_locked")
async def wallet_locked(callback: types.CallbackQuery):
    user = _get_user_row(callback.from_user.id)
    if user is None:
        await callback.answer("ابتدا دستور /start را بزنید.", show_alert=True)
        return
    text = (
        f"🔒 موجودی در انتظار شما\n\n{user['locked_wallet']:,} تومان\n\n"
        f"این مبلغ از دعوت دوستان به‌دست آمده و پس از اولین خرید آن‌ها، "
        f"به‌صورت خودکار به موجودی قابل‌استفاده شما اضافه می‌شود."
    )
    await callback.message.edit_text(text, reply_markup=back_button("profile", "🔙 بازگشت"))
    await callback.answer()


@router.callback_query(F.data == "transactions")
async def transactions(callback: types.CallbackQuery):
    user = _get_user_row(callback.from_user.id)
    if user is None:
        await callback.answer("ابتدا دستور /start را بزنید.", show_alert=True)
        return

    txs = db.get_transactions(user["id"], limit=10)
    if not txs:
        text = "📋 هنوز تراکنشی ندارید."
    else:
        icon_map = {
            "charge": "✅",
            "purchase": "🛒",
            "referral_locked": "🔒",
            "referral_release": "🔓",
        }
        text = "📋 تراکنش‌های اخیر:\n\n"
        for tx in txs:
            icon = icon_map.get(tx["type"], "•")
            text += f"{icon} {tx['description']} | {tx['amount']:,} تومان | {tx['created_at']}\n"

    await callback.message.edit_text(text, reply_markup=back_button("wallet", "🔙 بازگشت"))
    await callback.answer()
  # ---------------------------------------------------------------------------
# فرایند شارژ کیف پول
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "charge")
async def charge(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💳 مبلغ شارژ را انتخاب کنید:", reply_markup=charge_amount_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("charge_"))
async def charge_amount(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.replace("charge_", "")

    if action == "custom":
        await state.set_state(UserStates.waiting_custom_charge)
        await callback.message.edit_text("💵 مبلغ دلخواه را به تومان ارسال کنید:")
    else:
        amount = int(action)
        await state.update_data(amount=amount)
        await state.set_state(UserStates.waiting_charge_receipt)
        await callback.message.edit_text(
            f"💳 مبلغ: {amount:,} تومان\n\n"
            f"💳 شماره کارت:\n{CARD_NUMBER}\n\n"
            f"👤 {CARD_HOLDER}\n\n"
            f"📸 عکس رسید را ارسال کنید."
        )
    await callback.answer()


@router.message(UserStates.waiting_custom_charge)
async def custom_charge_amount(message: types.Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("❌ فقط عدد ارسال کنید.")
        return

    amount = int(message.text)
    await state.update_data(amount=amount)
    await state.set_state(UserStates.waiting_charge_receipt)
    await message.answer(
        f"✅ مبلغ {amount:,} تومان.\n\n"
        f"💳 شماره کارت:\n{CARD_NUMBER}\n\n"
        f"👤 {CARD_HOLDER}\n\n"
        f"📸 عکس رسید را ارسال کنید."
    )


@router.message(UserStates.waiting_charge_receipt, F.photo)
async def receive_receipt(message: types.Message, state: FSMContext):
    uid = str(message.from_user.id)
    data = await state.get_data()
    amount = data.get("amount")

    if amount is None:
        await message.answer("❌ مشکلی پیش آمد، لطفاً دوباره از منوی شارژ شروع کنید.")
        await state.clear()
        return

    await message.bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    await message.bot.send_message(
        ADMIN_ID,
        f"📩 رسید شارژ\n👤 {message.from_user.full_name}\n🆔 {uid}\n💰 {amount:,} تومان",
        reply_markup=admin_charge_approval_keyboard(uid, amount),
    )
    await message.answer("✅ رسید ثبت شد. پس از تأیید ادمین، کیف پول شما شارژ می‌شود.")
    await state.clear()


@router.message(UserStates.waiting_charge_receipt)
async def receipt_wrong_format(message: types.Message):
    # اگر کاربر به‌جای عکس، متن فرستاد
    await message.answer("📸 لطفاً عکس رسید پرداخت را ارسال کنید (نه متن).")
