"""
bot.py
فایل اصلی اجرای ربات. تمام Routerهای پوشه‌ی handlers اینجا به Dispatcher
وصل می‌شوند. یک سرور Flask کوچک هم کنارش اجرا می‌شود تا Render سرویس را
"زنده" تشخیص بدهد (لازمه‌ی سرویس‌های نوع Web Service).
"""

import asyncio
import logging
import os
import threading

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from flask import Flask

import database as db
from config import TOKEN
from handlers import start, wallet, profile, referral, plans, ticket, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Flask - فقط برای زنده نگه داشتن سرویس روی Render
# ---------------------------------------------------------------------------
flask_app = Flask(__name__)


@flask_app.route("/")
def health_check():
    return "Bot is running ✅"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)


# ---------------------------------------------------------------------------
# aiogram - ربات اصلی
# ---------------------------------------------------------------------------
async def run_bot():
    db.init_db()
    logger.info("Database initialized.")

    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # ترتیب ثبت Routerها مهم است: handler خاص‌تر باید زودتر بیاید.
    # admin باید قبل از بقیه باشد چون فیلتر سخت‌گیرانه‌تری (ADMIN_ID) دارد
    # و برخی callback_dataهای مشترک (مثل state یکسان) را زودتر می‌گیرد.
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(wallet.router)
    dp.include_router(profile.router)
    dp.include_router(referral.router)
    dp.include_router(plans.router)
    dp.include_router(ticket.router)

    logger.info("Bot starting polling...")
    await dp.start_polling(bot)


def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask keep-alive server started.")

    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
