"""
keyboards.py
تمام کیبوردهای Inline ربات. هیچ handlerای نباید خودش InlineKeyboardMarkup
بسازد؛ همه از این فایل صدا زده می‌شوند تا تغییر ظاهر منو در یک‌جا متمرکز باشد.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import VIP_PLANS, GAMING_PLANS, PLANS


def join_channels_keyboard(channels):
    buttons = [[InlineKeyboardButton(text=f"📢 {ch['name']}", url=ch["url"])] for ch in channels]
    buttons.append([InlineKeyboardButton(text="✅ عضو شدم", callback_data="check_join")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 سرویس‌ها", callback_data="plans")],
        [InlineKeyboardButton(text="💰 کیف پول", callback_data="wallet")],
        [InlineKeyboardButton(text="👥 معرفی دوستان", callback_data="referral")],
        [InlineKeyboardButton(text="👤 کاربران", callback_data="profile")],
        [InlineKeyboardButton(text="👨‍💻 تماس با پشتیبانی", callback_data="ticket")],
    ])


def back_button(callback_data: str = "back", text: str = "🏠 بازگشت به منوی اصلی"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=callback_data)]])


def profile_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 کیف پول آزاد", callback_data="wallet_free")],
        [InlineKeyboardButton(text="🔒 کیف پول مسدود", callback_data="wallet_locked")],
        [InlineKeyboardButton(text="🛒 تاریخچه خرید", callback_data="purchase_history")],
        [InlineKeyboardButton(text="📋 تاریخچه تراکنش", callback_data="transactions")],
        [InlineKeyboardButton(text="🔗 لینک دعوت اختصاصی", callback_data="referral")],
        [InlineKeyboardButton(text="🏠 بازگشت به منوی اصلی", callback_data="back")],
    ])


def wallet_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 شارژ کیف پول", callback_data="charge")],
        [InlineKeyboardButton(text="📋 تراکنش‌های من", callback_data="transactions")],
        [InlineKeyboardButton(text="🏠 بازگشت به منوی اصلی", callback_data="back")],
    ])


def charge_amount_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 ۵۰,۰۰۰ تومان", callback_data="charge_50000")],
        [InlineKeyboardButton(text="💰 ۱۰۰,۰۰۰ تومان", callback_data="charge_100000")],
        [InlineKeyboardButton(text="💰 ۲۰۰,۰۰۰ تومان", callback_data="charge_200000")],
        [InlineKeyboardButton(text="💵 مبلغ دلخواه", callback_data="charge_custom")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="wallet")],
    ])


def referral_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 بازگشت به منوی اصلی", callback_data="back")],
    ])


def services_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 VIP", callback_data="plans_vip")],
        [InlineKeyboardButton(text="🎮 Gaming", callback_data="plans_gaming")],
        [InlineKeyboardButton(text="🎟 کد تخفیف دارم", callback_data="use_discount")],
        [InlineKeyboardButton(text="📱 سرویس‌های من", callback_data="my_configs")],
        [InlineKeyboardButton(text="🏠 بازگشت به منوی اصلی", callback_data="back")],
    ])


def _plans_keyboard(plans_dict: dict, icon: str, discount_percent: int = 0):
    buttons = []
    for key, plan in plans_dict.items():
        price = plan["price"]
        if discount_percent:
            price = int(price * (1 - discount_percent / 100))
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {plan['name']} — {price:,} تومان",
            callback_data=f"buy_{key}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="plans")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vip_plans_keyboard(discount_percent: int = 0):
    return _plans_keyboard(VIP_PLANS, "👑", discount_percent)


def gaming_plans_keyboard(discount_percent: int = 0):
    return _plans_keyboard(GAMING_PLANS, "🎮", discount_percent)


def all_plans_discount_keyboard(discount_percent: int):
    return _plans_keyboard(PLANS, "📅", discount_percent)


def buy_confirm_keyboard(plan_key: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأیید خرید", callback_data=f"confirm_{plan_key}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="plans")],
    ])


def insufficient_balance_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 شارژ کیف پول", callback_data="wallet")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="plans")],
    ])
  def admin_panel_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔍 جستجوی حرفه‌ای", callback_data="admin_search")],
        [InlineKeyboardButton(text="💳 شارژ کیف پول", callback_data="admin_charge_wallet")],
        [InlineKeyboardButton(text="📤 ارسال کانفیگ", callback_data="admin_send_config")],
        [InlineKeyboardButton(text="🎟 مدیریت تخفیف", callback_data="admin_discount")],
        [InlineKeyboardButton(text="👥 مدیریت دعوت‌ها", callback_data="admin_referrals")],
        [InlineKeyboardButton(text="📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💾 بکاپ", callback_data="admin_backup")],
    ])


def admin_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_back")]])


def admin_discount_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ کد جدید", callback_data="new_discount")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_back")],
    ])


def admin_user_actions_keyboard(uid: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 شارژ دستی", callback_data=f"custom_{uid}")],
        [InlineKeyboardButton(text="📤 ارسال کانفیگ", callback_data=f"sendconfig_{uid}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_back")],
    ])


def admin_charge_approval_keyboard(uid: str, amount: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ تأیید {amount:,}", callback_data=f"approve_{uid}_{amount}")],
        [InlineKeyboardButton(text="💵 مبلغ دلخواه", callback_data=f"custom_{uid}")],
        [InlineKeyboardButton(text="❌ رد", callback_data=f"reject_{uid}")],
    ])


def admin_purchase_notify_keyboard(uid: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 ارسال کانفیگ", callback_data=f"sendconfig_{uid}")],
    ])


def ticket_reply_keyboard(uid: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ پاسخ", callback_data=f"replyticket_{uid}")],
    ])
