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
