"""
main.py
فایل اصلی اجرای ربات.
تمام routerهای پوشه‌ی handlers را به Dispatcher وصل می‌کند،
دیتابیس را مقداردهی اولیه می‌کند، و هم‌زمان یک سرور Flask کوچک
(برای زنده نگه داشتن سرویس روی Render) و polling تلگرام را اجرا می‌کند.
"""

import asyncio
import threading

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from flask import Flask

from config import TOKEN
import database as db

from handlers import start, plans, wallet, profile, referral, ticket, admin

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.include_router(start.router)
dp.include_router(plans.router)
dp.include_router(wallet.router)
dp.include_router(profile.router)
dp.include_router(referral.router)
dp.include_router(ticket.router)
dp.include_router(admin.router)

flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return "ربات در حال اجراست!"


def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)


async def main():
    db.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
