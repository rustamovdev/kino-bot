import aiosqlite
import datetime
from config import DB_PATH


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    joined_at TEXT,
    is_banned INTEGER DEFAULT 0,
    is_vip INTEGER DEFAULT 0,
    vip_until TEXT
);

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code INTEGER UNIQUE,
    title TEXT,
    category TEXT DEFAULT 'Umumiy',
    is_vip INTEGER DEFAULT 0,
    added_at TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    status TEXT DEFAULT 'kutilmoqda',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.execute(
            "INSERT OR IGNORE INTO categories (name) VALUES ('Umumiy')"
        )
        await db.commit()


# ---------------- USERS ----------------

async def add_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, joined_at) VALUES (?,?,?,?)",
                (user_id, username, full_name, now()),
            )
            await db.commit()
            return True  # yangi foydalanuvchi
        else:
            await db.execute(
                "UPDATE users SET username=?, full_name=? WHERE user_id=?",
                (username, full_name, user_id),
            )
            await db.commit()
            return False


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return await cur.fetchone()


async def is_banned(user_id: int) -> bool:
    u = await get_user(user_id)
    return bool(u["is_banned"]) if u else False


async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
        await db.commit()


async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
        await db.commit()


async def set_vip(user_id: int, days: int):
    until = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_vip=1, vip_until=? WHERE user_id=?", (until, user_id)
        )
        await db.commit()
    return until


async def remove_vip(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_vip=0, vip_until=NULL WHERE user_id=?", (user_id,)
        )
        await db.commit()


async def is_vip(user_id: int) -> bool:
    u = await get_user(user_id)
    if not u or not u["is_vip"]:
        return False
    if u["vip_until"]:
        try:
            until_dt = datetime.datetime.strptime(u["vip_until"], "%Y-%m-%d %H:%M:%S")
            if until_dt < datetime.datetime.now():
                await remove_vip(user_id)
                return False
        except ValueError:
            pass
    return True


async def all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users ORDER BY joined_at DESC")
        return await cur.fetchall()


async def vip_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE is_vip=1")
        return await cur.fetchall()


async def banned_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE is_banned=1")
        return await cur.fetchall()


async def users_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        row = await cur.fetchone()
        return row[0]


# ---------------- MOVIES ----------------

async def add_movie(code: int, title: str, category: str, is_vip_movie: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO movies (code, title, category, is_vip, added_at) VALUES (?,?,?,?,?)",
            (code, title, category, is_vip_movie, now()),
        )
        await db.commit()


async def get_movie(code: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM movies WHERE code=?", (code,))
        return await cur.fetchone()


async def delete_movie(code: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM movies WHERE code=?", (code,))
        await db.commit()
        return cur.rowcount > 0


async def edit_movie_title(code: int, title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE movies SET title=? WHERE code=?", (title, code))
        await db.commit()


async def edit_movie_category(code: int, category: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE movies SET category=? WHERE code=?", (category, code))
        await db.commit()


async def toggle_movie_vip(code: int, value: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE movies SET is_vip=? WHERE code=?", (value, code))
        await db.commit()


async def search_movies(query: str, limit: int = 15):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM movies WHERE title LIKE ? ORDER BY added_at DESC LIMIT ?",
            (f"%{query}%", limit),
        )
        return await cur.fetchall()


async def movies_by_category(category: str, limit: int = 30):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM movies WHERE category=? ORDER BY added_at DESC LIMIT ?",
            (category, limit),
        )
        return await cur.fetchall()


async def random_movie():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM movies ORDER BY RANDOM() LIMIT 1")
        return await cur.fetchone()


async def movies_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM movies")
        row = await cur.fetchone()
        return row[0]


async def last_movie_code():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT MAX(code) FROM movies")
        row = await cur.fetchone()
        return row[0] or 0


# ---------------- CATEGORIES ----------------

async def add_category(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def delete_category(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM categories WHERE name=?", (name,))
        await db.commit()
        return cur.rowcount > 0


async def all_categories():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM categories ORDER BY name")
        return await cur.fetchall()


# ---------------- ORDERS ----------------

async def add_order(user_id: int, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO orders (user_id, text, created_at) VALUES (?,?,?)",
            (user_id, text, now()),
        )
        await db.commit()


async def pending_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM orders WHERE status='kutilmoqda' ORDER BY created_at DESC"
        )
        return await cur.fetchall()


async def all_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders ORDER BY created_at DESC")
        return await cur.fetchall()


async def close_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status='bajarildi' WHERE id=?", (order_id,))
        await db.commit()


async def orders_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM orders")
        row = await cur.fetchone()
        return row[0]


# ---------------- SETTINGS ----------------

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()


async def get_setting(key: str, default: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default
