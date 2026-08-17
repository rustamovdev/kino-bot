"""
Database layer supporting both SQLite (local) and PostgreSQL (Supabase).
Automatically detects DATABASE_URL from config / environment.
"""
import asyncio
import datetime
import logging
from config import DB_PATH, DATABASE_URL


# PostgreSQL pool instance
_pg_pool = None


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_postgres() -> bool:
    return _pg_pool is not None



# ---------------- INITIALIZATION ----------------

SQLITE_SCHEMA = """
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

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    joined_at TEXT,
    is_banned INT DEFAULT 0,
    is_vip INT DEFAULT 0,
    vip_until TEXT
);

CREATE TABLE IF NOT EXISTS movies (
    id SERIAL PRIMARY KEY,
    code BIGINT UNIQUE,
    title TEXT,
    category TEXT DEFAULT 'Umumiy',
    is_vip INT DEFAULT 0,
    added_at TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
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
    global _pg_pool
    if DATABASE_URL and DATABASE_URL.strip().startswith(("postgres://", "postgresql://")):
        import asyncpg
        dsn = DATABASE_URL.replace("postgres://", "postgresql://")
        try:
            logging.info("🐘 PostgreSQL (Supabase) ga ulanish urinilmoqda...")
            _pg_pool = await asyncio.wait_for(
                asyncpg.create_pool(dsn=dsn, min_size=1, max_size=10, ssl="require"),
                timeout=12.0,
            )
            logging.info("🐘 PostgreSQL (Supabase) muvaffaqiyatli ulandi!")
            async with _pg_pool.acquire() as conn:
                for statement in PG_SCHEMA.strip().split(";"):
                    stmt = statement.strip()
                    if stmt:
                        await conn.execute(stmt)
                await conn.execute("INSERT INTO categories (name) VALUES ('Umumiy') ON CONFLICT (name) DO NOTHING")
            return
        except Exception as e:
            logging.error(f"PostgreSQL ulanishda xatolik: {e}")
            logging.info("📁 Zaxira rejim: SQLite ishlatilmoqda...")
            _pg_pool = None

    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SQLITE_SCHEMA)
        await db.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Umumiy')")
        await db.commit()
    logging.info("📁 SQLite (lokal baza) ulandi!")




# ---------------- USERS ----------------

async def add_user(user_id: int, username: str, full_name: str):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT user_id FROM users WHERE user_id = $1", user_id)
            if row is None:
                await conn.execute(
                    "INSERT INTO users (user_id, username, full_name, joined_at) VALUES ($1, $2, $3, $4)",
                    user_id, username, full_name, now()
                )
                return True
            else:
                await conn.execute(
                    "UPDATE users SET username = $1, full_name = $2 WHERE user_id = $3",
                    username, full_name, user_id
                )
                return False
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            if row is None:
                await db.execute(
                    "INSERT INTO users (user_id, username, full_name, joined_at) VALUES (?,?,?,?)",
                    (user_id, username, full_name, now()),
                )
                await db.commit()
                return True
            else:
                await db.execute(
                    "UPDATE users SET username=?, full_name=? WHERE user_id=?",
                    (username, full_name, user_id),
                )
                await db.commit()
                return False


async def get_user(user_id: int):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return dict(row) if row else None
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            return dict(row) if row else None


async def is_banned(user_id: int) -> bool:
    u = await get_user(user_id)
    return bool(u["is_banned"]) if u else False


async def ban_user(user_id: int):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = $1", user_id)
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
            await db.commit()


async def unban_user(user_id: int):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = $1", user_id)
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
            await db.commit()


async def set_vip(user_id: int, days: int):
    until = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_vip = 1, vip_until = $1 WHERE user_id = $2", until, user_id
            )
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET is_vip=1, vip_until=? WHERE user_id=?", (until, user_id)
            )
            await db.commit()
    return until


async def remove_vip(user_id: int):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_vip = 0, vip_until = NULL WHERE user_id = $1", user_id
            )
    else:
        import aiosqlite
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
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users ORDER BY joined_at DESC")
            return [dict(r) for r in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users ORDER BY joined_at DESC")
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def vip_users():
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users WHERE is_vip = 1")
            return [dict(r) for r in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE is_vip=1")
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def banned_users():
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users WHERE is_banned = 1")
            return [dict(r) for r in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE is_banned=1")
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def users_count():
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM users")
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users")
            row = await cur.fetchone()
            return row[0]


# ---------------- MOVIES ----------------

async def add_movie(code: int, title: str, category: str, is_vip_movie: int = 0):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO movies (code, title, category, is_vip, added_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (code) DO UPDATE SET
                    title = EXCLUDED.title,
                    category = EXCLUDED.category,
                    is_vip = EXCLUDED.is_vip,
                    added_at = EXCLUDED.added_at
                """,
                code, title, category, is_vip_movie, now()
            )
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO movies (code, title, category, is_vip, added_at) VALUES (?,?,?,?,?)",
                (code, title, category, is_vip_movie, now()),
            )
            await db.commit()


async def get_movie(code: int):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM movies WHERE code = $1", code)
            return dict(row) if row else None
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM movies WHERE code=?", (code,))
            row = await cur.fetchone()
            return dict(row) if row else None


async def delete_movie(code: int):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            res = await conn.execute("DELETE FROM movies WHERE code = $1", code)
            return "DELETE 1" in res or "DELETE 0" not in res
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("DELETE FROM movies WHERE code=?", (code,))
            await db.commit()
            return cur.rowcount > 0


async def edit_movie_title(code: int, title: str):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute("UPDATE movies SET title = $1 WHERE code = $2", title, code)
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE movies SET title=? WHERE code=?", (title, code))
            await db.commit()


async def edit_movie_category(code: int, category: str):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute("UPDATE movies SET category = $1 WHERE code = $2", category, code)
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE movies SET category=? WHERE code=?", (category, code))
            await db.commit()


async def toggle_movie_vip(code: int, value: int):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute("UPDATE movies SET is_vip = $1 WHERE code = $2", value, code)
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE movies SET is_vip=? WHERE code=?", (value, code))
            await db.commit()


async def search_movies(query: str, limit: int = 50, offset: int = 0):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM movies WHERE title ILIKE $1 ORDER BY added_at DESC LIMIT $2 OFFSET $3",
                f"%{query}%", limit, offset
            )
            return [dict(r) for r in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM movies WHERE title LIKE ? ORDER BY added_at DESC LIMIT ? OFFSET ?",
                (f"%{query}%", limit, offset),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def movies_by_category(category: str, limit: int = 30):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM movies WHERE category = $1 ORDER BY added_at DESC LIMIT $2",
                category, limit
            )
            return [dict(r) for r in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM movies WHERE category=? ORDER BY added_at DESC LIMIT ?",
                (category, limit),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def random_movie():
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM movies ORDER BY RANDOM() LIMIT 1")
            return dict(row) if row else None
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM movies ORDER BY RANDOM() LIMIT 1")
            row = await cur.fetchone()
            return dict(row) if row else None


async def movies_count():
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM movies")
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*) FROM movies")
            row = await cur.fetchone()
            return row[0]


async def last_movie_code():
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            val = await conn.fetchval("SELECT MAX(code) FROM movies")
            return val or 0
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT MAX(code) FROM movies")
            row = await cur.fetchone()
            return row[0] or 0


# ---------------- CATEGORIES ----------------

async def add_category(name: str):
    if is_postgres():
        try:
            async with _pg_pool.acquire() as conn:
                await conn.execute("INSERT INTO categories (name) VALUES ($1)", name)
                return True
        except Exception:
            return False
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False


async def delete_category(name: str):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            res = await conn.execute("DELETE FROM categories WHERE name = $1", name)
            return "DELETE 1" in res or "DELETE 0" not in res
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("DELETE FROM categories WHERE name=?", (name,))
            await db.commit()
            return cur.rowcount > 0


async def all_categories():
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM categories ORDER BY name")
            return [dict(r) for r in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM categories ORDER BY name")
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ---------------- ORDERS ----------------

async def add_order(user_id: int, text: str):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO orders (user_id, text, created_at) VALUES ($1, $2, $3)",
                user_id, text, now()
            )
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO orders (user_id, text, created_at) VALUES (?,?,?)",
                (user_id, text, now()),
            )
            await db.commit()


async def pending_orders():
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM orders WHERE status = 'kutilmoqda' ORDER BY created_at DESC")
            return [dict(r) for r in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM orders WHERE status='kutilmoqda' ORDER BY created_at DESC"
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def all_orders():
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM orders ORDER BY created_at DESC")
            return [dict(r) for r in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM orders ORDER BY created_at DESC")
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def close_order(order_id: int):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute("UPDATE orders SET status = 'bajarildi' WHERE id = $1", order_id)
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET status='bajarildi' WHERE id=?", (order_id,))
            await db.commit()


async def orders_count():
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM orders")
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*) FROM orders")
            row = await cur.fetchone()
            return row[0]


# ---------------- SETTINGS ----------------

async def set_setting(key: str, value: str):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO settings (key, value) VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
                key, value
            )
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            await db.commit()


async def get_setting(key: str, default: str = None):
    if is_postgres():
        async with _pg_pool.acquire() as conn:
            val = await conn.fetchval("SELECT value FROM settings WHERE key = $1", key)
            return val if val is not None else default
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = await cur.fetchone()
            return row[0] if row else default
