import aiosqlite
from typing import Optional, List, Tuple
from dataclasses import dataclass

@dataclass
class User:
    id: int
    tg_id: int
    is_active: bool
    allow_dues_notifications: bool
    allow_vpn_notifications: bool

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_id INTEGER UNIQUE NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 0,
  allow_dues_notifications INTEGER NOT NULL DEFAULT 1,
    allow_vpn_notifications INTEGER NOT NULL DEFAULT 1,
    show_status INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('dues','vpn')),
  amount INTEGER NOT NULL,
  paid_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('dues','vpn')),
  last_sent_at TEXT,
  acknowledged INTEGER NOT NULL DEFAULT 1,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""

class DAO:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def get_or_create_user(self, tg_id: int) -> User:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
            row = await cur.fetchone()
            if row:
                return User(row["id"], row["tg_id"], bool(row["is_active"]), bool(row["allow_dues_notifications"]), bool(row["allow_vpn_notifications"]))
            await db.execute("INSERT INTO users (tg_id) VALUES (?)", (tg_id,))
            await db.commit()
            cur = await db.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
            row = await cur.fetchone()
            return User(row["id"], row["tg_id"], bool(row["is_active"]), bool(row["allow_dues_notifications"]), bool(row["allow_vpn_notifications"]))

    async def activate_user(self, tg_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET is_active=1 WHERE tg_id=?", (tg_id,))
            await db.commit()

    async def set_notifications(self, user_id: int, dues: Optional[bool]=None, vpn: Optional[bool]=None):
        async with aiosqlite.connect(self.db_path) as db:
            if dues is not None:
                await db.execute("UPDATE users SET allow_dues_notifications=? WHERE id=?", (1 if dues else 0, user_id))
            if vpn is not None:
                await db.execute("UPDATE users SET allow_vpn_notifications=? WHERE id=?", (1 if vpn else 0, user_id))
            await db.commit()

    async def set_show_status(self, user_id: int, show: bool):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET show_status=? WHERE id=?", (1 if show else 0, user_id))
            await db.commit()

    async def get_show_status(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT show_status FROM users WHERE id=?", (user_id,))
            row = await cur.fetchone()
            return bool(row[0]) if row else True

    async def record_payment(self, user_id: int, type_: str, amount: int, paid_at: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO payments (user_id,type,amount,paid_at) VALUES (?,?,?,?)",
                (user_id, type_, amount, paid_at)
            )
            await db.commit()

    async def get_total_collected(self, type_: Optional[str]=None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            if type_:
                cur = await db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE type=?", (type_,))
            else:
                cur = await db.execute("SELECT COALESCE(SUM(amount),0) FROM payments")
            row = await cur.fetchone()
            return int(row[0] or 0)

    async def set_savings(self, amount: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO settings(key,value) VALUES('savings',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(amount),))
            await db.commit()

    async def get_savings(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT value FROM settings WHERE key='savings'")
            row = await cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

    async def upsert_reminder(self, user_id: int, type_: str, acknowledged: bool, last_sent_at: Optional[str]):
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT id FROM reminders WHERE user_id=? AND type=?", (user_id, type_))
            row = await cur.fetchone()
            if row:
                await db.execute("UPDATE reminders SET acknowledged=?, last_sent_at=? WHERE id=?", (1 if acknowledged else 0, last_sent_at, row[0]))
            else:
                await db.execute("INSERT INTO reminders(user_id,type,acknowledged,last_sent_at) VALUES (?,?,?,?)", (user_id, type_, 1 if acknowledged else 0, last_sent_at))
            await db.commit()

    async def users_for_reminder(self, type_: str) -> List[Tuple[int,int]]:
        async with aiosqlite.connect(self.db_path) as db:
            notif_col = "allow_dues_notifications" if type_ == "dues" else "allow_vpn_notifications"
            cur = await db.execute(
                f"SELECT u.id, u.tg_id FROM users u LEFT JOIN reminders r ON r.user_id=u.id AND r.type=? "
                f"WHERE u.is_active=1 AND u.{notif_col}=1 AND (r.acknowledged=0 OR r.id IS NULL)",
                (type_,)
            )
            return [(row[0], row[1]) for row in await cur.fetchall()]

    async def get_schedule_time(self) -> Tuple[int, int]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT value FROM settings WHERE key='reminder_hour'")
            row_h = await cur.fetchone()
            cur = await db.execute("SELECT value FROM settings WHERE key='reminder_minute'")
            row_m = await cur.fetchone()
            hour = int(row_h[0]) if row_h and row_h[0] is not None else 9
            minute = int(row_m[0]) if row_m and row_m[0] is not None else 0
            return hour, minute

    async def set_schedule_time(self, hour: int, minute: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO settings(key,value) VALUES('reminder_hour',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(hour),))
            await db.execute("INSERT INTO settings(key,value) VALUES('reminder_minute',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(minute),))
            await db.commit()
