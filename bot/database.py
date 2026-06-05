import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bot.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                reason TEXT,
                banned_by TEXT,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                permanent INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ip_bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                reason TEXT,
                banned_by TEXT,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                guild_id TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alt_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                main_user_id TEXT NOT NULL,
                alt_user_id TEXT NOT NULL,
                registered_by TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                guild_id TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ip_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                registered_by TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS raid_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                event TEXT NOT NULL,
                user_id TEXT,
                details TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mod_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                action TEXT NOT NULL,
                target_id TEXT NOT NULL,
                moderator_id TEXT NOT NULL,
                reason TEXT,
                extra TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS economy (
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                coins INTEGER DEFAULT 0,
                last_daily TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                quantity INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_attempts (
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                date TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id, date)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shields (
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.commit()


async def get_coins(user_id: str, guild_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT coins FROM economy WHERE user_id=? AND guild_id=?", (user_id, guild_id)
        ) as c:
            row = await c.fetchone()
            return row[0] if row else 0


async def add_coins(user_id: str, guild_id: str, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO economy (user_id, guild_id, coins) VALUES (?,?,?) ON CONFLICT(user_id,guild_id) DO UPDATE SET coins=coins+?",
            (user_id, guild_id, max(0, amount), amount)
        )
        await db.commit()


async def set_coins(user_id: str, guild_id: str, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO economy (user_id, guild_id, coins) VALUES (?,?,?) ON CONFLICT(user_id,guild_id) DO UPDATE SET coins=?",
            (user_id, guild_id, amount, amount)
        )
        await db.commit()


async def get_last_daily(user_id: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_daily FROM economy WHERE user_id=? AND guild_id=?", (user_id, guild_id)
        ) as c:
            row = await c.fetchone()
            return row[0] if row else None


async def set_last_daily(user_id: str, guild_id: str, date_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO economy (user_id, guild_id, coins, last_daily) VALUES (?,?,0,?) ON CONFLICT(user_id,guild_id) DO UPDATE SET last_daily=?",
            (user_id, guild_id, date_str, date_str)
        )
        await db.commit()


async def get_inventory(user_id: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT item_id, quantity FROM inventory WHERE user_id=? AND guild_id=?", (user_id, guild_id)
        ) as c:
            return await c.fetchall()


async def add_item(user_id: str, guild_id: str, item_id: str, qty: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await db.execute(
            "SELECT id, quantity FROM inventory WHERE user_id=? AND guild_id=? AND item_id=?",
            (user_id, guild_id, item_id)
        )
        row = await existing.fetchone()
        if row:
            await db.execute("UPDATE inventory SET quantity=quantity+? WHERE id=?", (qty, row[0]))
        else:
            await db.execute(
                "INSERT INTO inventory (user_id, guild_id, item_id, quantity) VALUES (?,?,?,?)",
                (user_id, guild_id, item_id, qty)
            )
        await db.commit()


async def remove_item(user_id: str, guild_id: str, item_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await db.execute(
            "SELECT id, quantity FROM inventory WHERE user_id=? AND guild_id=? AND item_id=?",
            (user_id, guild_id, item_id)
        )
        row = await existing.fetchone()
        if not row or row[1] < 1:
            return False
        if row[1] == 1:
            await db.execute("DELETE FROM inventory WHERE id=?", (row[0],))
        else:
            await db.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=?", (row[0],))
        await db.commit()
        return True


async def get_game_attempts(user_id: str, guild_id: str, date_str: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT attempts FROM game_attempts WHERE user_id=? AND guild_id=? AND date=?",
            (user_id, guild_id, date_str)
        ) as c:
            row = await c.fetchone()
            return row[0] if row else 0


async def increment_game_attempts(user_id: str, guild_id: str, date_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO game_attempts (user_id, guild_id, date, attempts) VALUES (?,?,?,1) ON CONFLICT(user_id,guild_id,date) DO UPDATE SET attempts=attempts+1",
            (user_id, guild_id, date_str)
        )
        await db.commit()


async def get_top_coins(guild_id: str, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, coins FROM economy WHERE guild_id=? ORDER BY coins DESC LIMIT ?",
            (guild_id, limit)
        ) as c:
            return await c.fetchall()


async def has_shield(user_id: str, guild_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT expires_at FROM shields WHERE user_id=? AND guild_id=?", (user_id, guild_id)
        ) as c:
            row = await c.fetchone()
            if not row:
                return False
            from datetime import datetime, timezone
            expires = datetime.fromisoformat(row[0])
            if datetime.now(timezone.utc) > expires:
                await db.execute("DELETE FROM shields WHERE user_id=? AND guild_id=?", (user_id, guild_id))
                await db.commit()
                return False
            return True


async def set_shield(user_id: str, guild_id: str, expires_at: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO shields (user_id, guild_id, expires_at) VALUES (?,?,?) ON CONFLICT(user_id,guild_id) DO UPDATE SET expires_at=?",
            (user_id, guild_id, expires_at, expires_at)
        )
        await db.commit()


async def add_ban(user_id: str, guild_id: str, reason: str, banned_by: str, expires_at=None):
    permanent = 1 if expires_at is None else 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bans (user_id, guild_id, reason, banned_by, expires_at, permanent) VALUES (?,?,?,?,?,?)",
            (user_id, guild_id, reason, banned_by, expires_at, permanent)
        )
        await db.commit()


async def remove_ban(user_id: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bans WHERE user_id=? AND guild_id=?", (user_id, guild_id))
        await db.commit()


async def is_banned(user_id: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM bans WHERE user_id=? AND guild_id=? AND (permanent=1 OR expires_at > datetime('now'))",
            (user_id, guild_id)
        ) as cursor:
            return await cursor.fetchone()


async def add_ip_ban(ip: str, guild_id: str, reason: str, banned_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ip_bans (ip_address, guild_id, reason, banned_by) VALUES (?,?,?,?)",
            (ip, guild_id, reason, banned_by)
        )
        await db.commit()


async def remove_ip_ban(ip: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM ip_bans WHERE ip_address=? AND guild_id=?", (ip, guild_id))
        await db.commit()


async def is_ip_banned(ip: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM ip_bans WHERE ip_address=? AND guild_id=?",
            (ip, guild_id)
        ) as cursor:
            return await cursor.fetchone()


async def register_ip(user_id: str, ip: str, guild_id: str, registered_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await db.execute(
            "SELECT id FROM ip_registry WHERE user_id=? AND ip_address=? AND guild_id=?",
            (user_id, ip, guild_id)
        )
        row = await existing.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO ip_registry (user_id, ip_address, guild_id, registered_by) VALUES (?,?,?,?)",
                (user_id, ip, guild_id, registered_by)
            )
            await db.commit()


async def get_users_by_ip(ip: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM ip_registry WHERE ip_address=? AND guild_id=?",
            (ip, guild_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


async def get_ips_by_user(user_id: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT ip_address FROM ip_registry WHERE user_id=? AND guild_id=?",
            (user_id, guild_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


async def register_alt(main_id: str, alt_id: str, guild_id: str, registered_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO alt_accounts (main_user_id, alt_user_id, guild_id, registered_by) VALUES (?,?,?,?)",
            (main_id, alt_id, guild_id, registered_by)
        )
        await db.commit()


async def get_alts(user_id: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT alt_user_id FROM alt_accounts WHERE main_user_id=? AND guild_id=?",
            (user_id, guild_id)
        ) as cursor:
            rows = await cursor.fetchall()
            alts = [r[0] for r in rows]
        async with db.execute(
            "SELECT main_user_id FROM alt_accounts WHERE alt_user_id=? AND guild_id=?",
            (user_id, guild_id)
        ) as cursor:
            rows = await cursor.fetchall()
            mains = [r[0] for r in rows]
        return alts, mains


async def log_mod_action(guild_id: str, action: str, target_id: str, moderator_id: str, reason: str, extra: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO mod_log (guild_id, action, target_id, moderator_id, reason, extra) VALUES (?,?,?,?,?,?)",
            (guild_id, action, target_id, moderator_id, reason, extra)
        )
        await db.commit()


async def log_raid_event(guild_id: str, event: str, user_id: str = None, details: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO raid_log (guild_id, event, user_id, details) VALUES (?,?,?,?)",
            (guild_id, event, user_id, details)
        )
        await db.commit()


async def get_mod_log(guild_id: str, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT action, target_id, moderator_id, reason, extra, executed_at FROM mod_log WHERE guild_id=? ORDER BY executed_at DESC LIMIT ?",
            (guild_id, limit)
        ) as cursor:
            return await cursor.fetchall()


async def get_all_ip_bans(guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT ip_address, reason, banned_by, banned_at FROM ip_bans WHERE guild_id=? ORDER BY banned_at DESC",
            (guild_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_all_bans(guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, reason, banned_by, banned_at, expires_at, permanent FROM bans WHERE guild_id=? ORDER BY banned_at DESC",
            (guild_id,)
        ) as cursor:
            return await cursor.fetchall()
