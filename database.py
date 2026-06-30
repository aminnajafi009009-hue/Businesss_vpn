"""
database.py
لایه‌ی کامل دسترسی به دیتابیس SQLite.
هیچ فایل دیگری در پروژه نباید مستقیماً sqlite3 را import کند؛
همه باید از طریق توابع همین فایل با دیتابیس کار کنند.
"""

import sqlite3
import threading
import secrets
import string
from contextlib import contextmanager
from datetime import datetime

from config import DATABASE_PATH, REFERRAL_LOCK_AMOUNT

_local = threading.local()
_lock = threading.Lock()  # برای جلوگیری از تداخل نوشتن همزمان


def get_connection() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        _local.conn = conn
    return _local.conn


@contextmanager
def transaction():
    conn = get_connection()
    cur = conn.cursor()
    with _lock:
        try:
            cur.execute("BEGIN")
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id         TEXT UNIQUE NOT NULL,
            name                TEXT NOT NULL,
            wallet              INTEGER NOT NULL DEFAULT 0,
            locked_wallet       INTEGER NOT NULL DEFAULT 0,
            total_purchase      INTEGER NOT NULL DEFAULT 0,
            joined              TEXT NOT NULL,
            referrer_id         INTEGER,
            invite_code         TEXT UNIQUE NOT NULL,
            invited_count       INTEGER NOT NULL DEFAULT 0,
            successful_invites  INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (referrer_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            type        TEXT NOT NULL,
            amount      INTEGER NOT NULL,
            status      TEXT NOT NULL DEFAULT 'completed',
            description TEXT,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            plan        TEXT NOT NULL,
            config      TEXT NOT NULL,
            expiry      TEXT,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS discounts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT UNIQUE NOT NULL,
            percent     INTEGER NOT NULL,
            uses        INTEGER NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id   INTEGER NOT NULL,
            invited_id    INTEGER NOT NULL UNIQUE,
            reward        INTEGER NOT NULL DEFAULT 0,
            status        TEXT NOT NULL DEFAULT 'pending',
            created_at    TEXT NOT NULL,
            FOREIGN KEY (referrer_id) REFERENCES users(id),
            FOREIGN KEY (invited_id) REFERENCES users(id)
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_invite_code ON users(invite_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_configs_user ON configs(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)")

    conn.commit()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _generate_invite_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "BVPN" + "".join(secrets.choice(alphabet) for _ in range(5))
        cur = get_connection().cursor()
        cur.execute("SELECT 1 FROM users WHERE invite_code = ?", (code,))
        if cur.fetchone() is None:
            return code
    def get_user(telegram_id) -> sqlite3.Row | None:
    cur = get_connection().cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (str(telegram_id),))
    return cur.fetchone()


def get_user_by_invite_code(code: str) -> sqlite3.Row | None:
    cur = get_connection().cursor()
    cur.execute("SELECT * FROM users WHERE invite_code = ?", (code.upper(),))
    return cur.fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    cur = get_connection().cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cur.fetchone()


def create_user(telegram_id, name: str, referrer_invite_code: str | None = None) -> sqlite3.Row:
    telegram_id = str(telegram_id)
    existing = get_user(telegram_id)
    if existing:
        return existing

    referrer = None
    if referrer_invite_code:
        referrer = get_user_by_invite_code(referrer_invite_code)
        if referrer and referrer["telegram_id"] == telegram_id:
            referrer = None

    invite_code = _generate_invite_code()

    with transaction() as cur:
        cur.execute(
            """INSERT INTO users (telegram_id, name, wallet, locked_wallet,
                                   total_purchase, joined, referrer_id, invite_code,
                                   invited_count, successful_invites)
               VALUES (?, ?, 0, 0, 0, ?, ?, ?, 0, 0)""",
            (telegram_id, name, _now(), referrer["id"] if referrer else None, invite_code),
        )
        new_user_id = cur.lastrowid

        if referrer:
            cur.execute(
                """INSERT INTO referrals (referrer_id, invited_id, reward, status, created_at)
                   VALUES (?, ?, ?, 'pending', ?)""",
                (referrer["id"], new_user_id, REFERRAL_LOCK_AMOUNT, _now()),
            )
            cur.execute(
                "UPDATE users SET invited_count = invited_count + 1 WHERE id = ?",
                (referrer["id"],),
            )
            cur.execute(
                "UPDATE users SET locked_wallet = locked_wallet + ? WHERE id = ?",
                (REFERRAL_LOCK_AMOUNT, referrer["id"]),
            )
            cur.execute(
                """INSERT INTO transactions (user_id, type, amount, status, description, created_at)
                   VALUES (?, 'referral_locked', ?, 'pending', ?, ?)""",
                (referrer["id"], REFERRAL_LOCK_AMOUNT, "پاداش دعوت (در انتظار اولین خرید)", _now()),
            )

    return get_user(telegram_id)


def update_user_name(telegram_id, name: str):
    with transaction() as cur:
        cur.execute("UPDATE users SET name = ? WHERE telegram_id = ?", (name, str(telegram_id)))


def get_all_users(limit: int | None = None) -> list[sqlite3.Row]:
    cur = get_connection().cursor()
    if limit:
        cur.execute("SELECT * FROM users ORDER BY id DESC LIMIT ?", (limit,))
    else:
        cur.execute("SELECT * FROM users ORDER BY id DESC")
    return cur.fetchall()


def count_users() -> int:
    cur = get_connection().cursor()
    cur.execute("SELECT COUNT(*) AS c FROM users")
    return cur.fetchone()["c"]


def count_active_users(days: int = 30) -> int:
    cur = get_connection().cursor()
    cur.execute(
        """SELECT COUNT(DISTINCT user_id) AS c FROM transactions
           WHERE created_at >= datetime('now', ?)""",
        (f"-{days} days",),
    )
    return cur.fetchone()["c"]


def add_to_wallet(user_id: int, amount: int, description: str, tx_type: str = "charge"):
    with transaction() as cur:
        cur.execute("UPDATE users SET wallet = wallet + ? WHERE id = ?", (amount, user_id))
        cur.execute(
            """INSERT INTO transactions (user_id, type, amount, status, description, created_at)
               VALUES (?, ?, ?, 'completed', ?, ?)""",
            (user_id, tx_type, amount, description, _now()),
        )


def add_to_locked_wallet(user_id: int, amount: int, description: str):
    with transaction() as cur:
        cur.execute("UPDATE users SET locked_wallet = locked_wallet + ? WHERE id = ?", (amount, user_id))
        cur.execute(
            """INSERT INTO transactions (user_id, type, amount, status, description, created_at)
               VALUES (?, 'referral_pending', ?, 'pending', ?, ?)""",
            (user_id, amount, description, _now()),
        )


def release_locked_wallet(user_id: int, amount: int, description: str = "آزادسازی پاداش دعوت"):
    with transaction() as cur:
        cur.execute("SELECT locked_wallet FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row is None or row["locked_wallet"] < amount:
            raise ValueError("موجودی در انتظار کافی نیست.")
        cur.execute(
            "UPDATE users SET locked_wallet = locked_wallet - ?, wallet = wallet + ? WHERE id = ?",
            (amount, amount, user_id),
        )
        cur.execute(
            """INSERT INTO transactions (user_id, type, amount, status, description, created_at)
               VALUES (?, 'referral_release', ?, 'completed', ?, ?)""",
            (user_id, amount, description, _now()),
        )


def deduct_from_wallet(user_id: int, amount: int, description: str) -> bool:
    with transaction() as cur:
        cur.execute("SELECT wallet FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row is None or row["wallet"] < amount:
            return False
        cur.execute(
            "UPDATE users SET wallet = wallet - ?, total_purchase = total_purchase + ? WHERE id = ?",
            (amount, amount, user_id),
        )
        cur.execute(
            """INSERT INTO transactions (user_id, type, amount, status, description, created_at)
               VALUES (?, 'purchase', ?, 'completed', ?, ?)""",
            (user_id, amount, description, _now()),
        )
    return True


def get_transactions(user_id: int, limit: int = 10) -> list[sqlite3.Row]:
    cur = get_connection().cursor()
    cur.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    return cur.fetchall()


def total_sales() -> int:
    cur = get_connection().cursor()
    cur.execute("SELECT COALESCE(SUM(amount), 0) AS s FROM transactions WHERE type = 'purchase'")
    return cur.fetchone()["s"]


def sales_since(days: int) -> int:
    cur = get_connection().cursor()
    cur.execute(
        """SELECT COALESCE(SUM(amount), 0) AS s FROM transactions
           WHERE type = 'purchase' AND created_at >= datetime('now', ?)""",
        (f"-{days} days",),
    )
    return cur.fetchone()["s"]
  def add_config(user_id: int, plan_name: str, encrypted_config: str, expiry: str | None):
    with transaction() as cur:
        cur.execute(
            """INSERT INTO configs (user_id, plan, config, expiry, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, plan_name, encrypted_config, expiry, _now()),
        )


def get_configs(user_id: int) -> list[sqlite3.Row]:
    cur = get_connection().cursor()
    cur.execute("SELECT * FROM configs WHERE user_id = ? ORDER BY id DESC", (user_id,))
    return cur.fetchall()


def get_discount(code: str) -> sqlite3.Row | None:
    cur = get_connection().cursor()
    cur.execute("SELECT * FROM discounts WHERE code = ?", (code.upper(),))
    return cur.fetchone()


def create_discount(code: str, percent: int, uses: int):
    with transaction() as cur:
        cur.execute(
            "INSERT INTO discounts (code, percent, uses, created_at) VALUES (?, ?, ?, ?)",
            (code.upper(), percent, uses, _now()),
        )


def use_discount(code: str) -> bool:
    with transaction() as cur:
        cur.execute("SELECT uses FROM discounts WHERE code = ?", (code.upper(),))
        row = cur.fetchone()
        if row is None or row["uses"] <= 0:
            return False
        cur.execute("UPDATE discounts SET uses = uses - 1 WHERE code = ?", (code.upper(),))
    return True


def get_all_discounts() -> list[sqlite3.Row]:
    cur = get_connection().cursor()
    cur.execute("SELECT * FROM discounts ORDER BY id DESC")
    return cur.fetchall()


def get_referral(invited_id: int) -> sqlite3.Row | None:
    cur = get_connection().cursor()
    cur.execute("SELECT * FROM referrals WHERE invited_id = ?", (invited_id,))
    return cur.fetchone()


def complete_referral(invited_id: int):
    """
    وقتی فرد دعوت‌شده اولین خریدش را انجام داد فراخوانی می‌شود.
    - فقط رکوردهای status='pending' پردازش می‌شوند (جلوگیری از آزاد شدن دوباره).
    - مبلغی که موقع ثبت‌نام در locked_wallet معرف قفل شده بود، به wallet او منتقل می‌شود.
    """
    with transaction() as cur:
        cur.execute(
            "SELECT * FROM referrals WHERE invited_id = ? AND status = 'pending'",
            (invited_id,),
        )
        ref = cur.fetchone()
        if ref is None:
            return

        reward = ref["reward"]

        cur.execute(
            "SELECT locked_wallet FROM users WHERE id = ?", (ref["referrer_id"],)
        )
        referrer_row = cur.fetchone()
        if referrer_row is None or referrer_row["locked_wallet"] < reward:
            raise ValueError("موجودی قفل‌شده معرف برای آزادسازی کافی نیست.")

        cur.execute(
            "UPDATE referrals SET status = 'completed' WHERE id = ?",
            (ref["id"],),
        )
        cur.execute(
            "UPDATE users SET successful_invites = successful_invites + 1 WHERE id = ?",
            (ref["referrer_id"],),
        )
        cur.execute(
            "UPDATE users SET locked_wallet = locked_wallet - ?, wallet = wallet + ? WHERE id = ?",
            (reward, reward, ref["referrer_id"]),
        )
        cur.execute(
            """INSERT INTO transactions (user_id, type, amount, status, description, created_at)
               VALUES (?, 'referral_release', ?, 'completed', ?, ?)""",
            (ref["referrer_id"], reward, "آزادسازی پاداش دعوت (اولین خرید فرد دعوت‌شده)", _now()),
        )


def get_referral_stats(user_id: int) -> dict:
    user = get_user_by_id(user_id)
    cur = get_connection().cursor()
    cur.execute(
        "SELECT COALESCE(SUM(reward), 0) AS released FROM referrals WHERE referrer_id = ? AND status = 'completed'",
        (user_id,),
    )
    released = cur.fetchone()["released"]
    cur.execute(
        "SELECT COUNT(*) AS c FROM referrals WHERE referrer_id = ? AND status = 'pending'",
        (user_id,),
    )
    pending_count = cur.fetchone()["c"]
    return {
        "invite_code": user["invite_code"],
        "invited_count": user["invited_count"],
        "successful_invites": user["successful_invites"],
        "released_amount": released,
        "pending_count": pending_count,
}
