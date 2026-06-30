"""
config.py
تمام تنظیمات ربات از اینجا خوانده می‌شود.
هیچ مقدار حساس (توکن، آیدی ادمین، شماره کارت) نباید مستقیم داخل کد نوشته شود؛
همه از فایل .env خوانده می‌شوند.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def _get_env(key: str, required: bool = True, default=None):
    value = os.environ.get(key, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"متغیر محیطی الزامی '{key}' در فایل .env تنظیم نشده است.")
    return value

TOKEN = _get_env("TOKEN")
ADMIN_ID = int(_get_env("ADMIN_ID"))

CARD_NUMBER = _get_env("CARD_NUMBER")
CARD_HOLDER = _get_env("CARD_HOLDER")

DATABASE_PATH = _get_env("DATABASE_PATH", required=False, default="database.db")

REQUIRED_CHANNELS = [
    {"id": -1003957260685, "name": "کانال اصلی", "url": "https://t.me/businesss_vpn"},
    {"id": -1003904350377, "name": "کانال اعتماد", "url": "https://t.me/businesss_etemad"},
]

VIP_PLANS = {
    "plan_1": {"name": "10 گیگ | کاربر و زمان ∞", "price": 75000, "days": 0},
    "plan_3": {"name": "20 گیگ | کاربر و زمان ∞", "price": 150000, "days": 0},
    "plan_6": {"name": "30 گیگ | کاربر و زمان ∞", "price": 225000, "days": 0},
    "plan_7": {"name": "50 گیگ | کاربر و زمان ∞", "price": 300000, "days": 0},
    "plan_8": {"name": "100 گیگ | کاربر و زمان ∞", "price": 500000, "days": 0},
}

GAMING_PLANS = {
    "plan_9": {"name": "36 گیگ گیمینگ یک ماهه تک کاربر", "price": 149000, "days": 30},
    "plan_10": {"name": "78 گیگ گیمینگ دو ماهه تک کاربر", "price": 249000, "days": 60},
    "plan_11": {"name": "127 گیگ گیمینگ سه ماهه تک کاربر", "price": 419000, "days": 90},
    "plan_12": {"name": "300 گیگ گیمینگ شش ماهه تک کاربر", "price": 500000, "days": 180},
}

PLANS = {**VIP_PLANS, **GAMING_PLANS}

# مبلغی که با ثبت‌نام هر فرد دعوت‌شده، به‌صورت "قفل" به معرف تعلق می‌گیرد
# و فقط بعد از اولین خرید فرد دعوت‌شده آزاد می‌شود.
REFERRAL_LOCK_AMOUNT = int(_get_env("REFERRAL_LOCK_AMOUNT", required=False, default="40000"))
BOT_USERNAME = _get_env("BOT_USERNAME", required=False, default="BusinessSVPNBot")
