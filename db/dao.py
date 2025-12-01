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
    show_status INTEGER NOT NULL DEFAULT 1,
    show_dues INTEGER NOT NULL DEFAULT 1,
    show_vpn INTEGER NOT NULL DEFAULT 1,
    show_savings INTEGER NOT NULL DEFAULT 1
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

CREATE TABLE IF NOT EXISTS custom_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0,
    batch_id TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""

class DAO:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            # Миграция: добавить столбец show_status если отсутствует
            cur = await db.execute("PRAGMA table_info(users)")
            cols = [r[1] for r in await cur.fetchall()]
            if "show_status" not in cols:
                await db.execute("ALTER TABLE users ADD COLUMN show_status INTEGER NOT NULL DEFAULT 1")
            if "show_dues" not in cols:
                await db.execute("ALTER TABLE users ADD COLUMN show_dues INTEGER NOT NULL DEFAULT 1")
            if "show_vpn" not in cols:
                await db.execute("ALTER TABLE users ADD COLUMN show_vpn INTEGER NOT NULL DEFAULT 1")
            if "show_savings" not in cols:
                await db.execute("ALTER TABLE users ADD COLUMN show_savings INTEGER NOT NULL DEFAULT 1")
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

    async def get_component_visibility(self, user_id: int) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT show_dues, show_vpn, show_savings FROM users WHERE id=?", (user_id,))
            row = await cur.fetchone()
            if not row:
                return {"dues": True, "vpn": True, "savings": True}
            return {"dues": bool(row[0]), "vpn": bool(row[1]), "savings": bool(row[2])}

    async def toggle_component(self, user_id: int, component: str):
        col_map = {"dues": "show_dues", "vpn": "show_vpn", "savings": "show_savings"}
        if component not in col_map:
            return
        col = col_map[component]
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(f"SELECT {col} FROM users WHERE id=?", (user_id,))
            row = await cur.fetchone()
            current = bool(row[0]) if row else True
            await db.execute(f"UPDATE users SET {col}=? WHERE id=?", (0 if current else 1, user_id))
            await db.commit()

    async def total_users(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users")
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def users_page(self, page: int, page_size: int):
        offset = (page - 1) * page_size
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT id, tg_id, is_active, show_status, allow_dues_notifications, allow_vpn_notifications, show_dues, show_vpn, show_savings FROM users ORDER BY id LIMIT ? OFFSET ?",
                (page_size, offset)
            )
            rows = await cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "tg_id": r["tg_id"],
                    "active": bool(r["is_active"]),
                    "show_status": bool(r["show_status"]),
                    "dues": bool(r["allow_dues_notifications"]),
                    "vpn": bool(r["allow_vpn_notifications"]),
                    "show_dues": bool(r["show_dues"]),
                    "show_vpn": bool(r["show_vpn"]),
                    "show_savings": bool(r["show_savings"]),
                }
                for r in rows
            ]

    async def active_user_ids(self) -> list[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT tg_id FROM users WHERE is_active=1")
            return [r[0] for r in await cur.fetchall()]

    async def tg_to_internal_map(self, tg_ids: list[int]) -> dict[int,int]:
        if not tg_ids:
            return {}
        placeholders = ",".join("?" for _ in tg_ids)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(f"SELECT id, tg_id FROM users WHERE tg_id IN ({placeholders})", tuple(tg_ids))
            return {row["tg_id"]: row["id"] for row in await cur.fetchall()}

    async def create_custom_notifications(self, text: str, tg_ids: list[int], sent_at: str) -> int:
        # returns count sent
        if not tg_ids:
            return 0
        mapping = await self.tg_to_internal_map(tg_ids)
        async with aiosqlite.connect(self.db_path) as db:
            for tg_id in tg_ids:
                internal_id = mapping.get(tg_id)
                if internal_id is None:
                    # ensure user exists
                    await db.execute("INSERT OR IGNORE INTO users(tg_id) VALUES(?)", (tg_id,))
                    cur = await db.execute("SELECT id FROM users WHERE tg_id=?", (tg_id,))
                    row = await cur.fetchone()
                    internal_id = row[0]
                await db.execute(
                    "INSERT INTO custom_notifications(user_id,text,sent_at) VALUES (?,?,?)",
                    (internal_id, text, sent_at)
                )
            await db.commit()
        return len(tg_ids)

    async def create_custom_notifications_batch(self, text: str, tg_ids: list[int], sent_at: str, batch_id: str):
        mapping = await self.tg_to_internal_map(tg_ids)
        created = []  # list of tuples (tg_id, notif_id)
        async with aiosqlite.connect(self.db_path) as db:
            for tg_id in tg_ids:
                internal_id = mapping.get(tg_id)
                if internal_id is None:
                    await db.execute("INSERT OR IGNORE INTO users(tg_id) VALUES(?)", (tg_id,))
                    cur = await db.execute("SELECT id FROM users WHERE tg_id=?", (tg_id,))
                    row = await cur.fetchone()
                    internal_id = row[0]
                await db.execute(
                    "INSERT INTO custom_notifications(user_id,text,sent_at,batch_id) VALUES (?,?,?,?)",
                    (internal_id, text, sent_at, batch_id)
                )
                cur = await db.execute("SELECT last_insert_rowid()")
                row = await cur.fetchone()
                created.append((tg_id, row[0]))
            await db.commit()
        return created  # list of (tg_id, notif_id)

    async def acknowledge_custom(self, user_id: int, notif_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE custom_notifications SET acknowledged=1 WHERE id=? AND user_id=?",
                (notif_id, user_id)
            )
            await db.commit()

    async def get_custom_notif(self, notif_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM custom_notifications WHERE id=?", (notif_id,))
            row = await cur.fetchone()
            if not row:
                return None
            return {"id": row["id"], "user_id": row["user_id"], "text": row["text"], "sent_at": row["sent_at"], "acknowledged": bool(row["acknowledged"]), "batch_id": row["batch_id"]}

    async def list_batches(self, page: int, page_size: int):
        offset = (page - 1) * page_size
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT batch_id, text, sent_at, COUNT(*) AS total, SUM(acknowledged) AS acked "
                "FROM custom_notifications GROUP BY batch_id, text, sent_at ORDER BY sent_at DESC LIMIT ? OFFSET ?",
                (page_size, offset)
            )
            rows = await cur.fetchall()
            return [
                {
                    "batch_id": r["batch_id"],
                    "text": r["text"],
                    "sent_at": r["sent_at"],
                    "total": r["total"],
                    "acked": r["acked"] if r["acked"] is not None else 0,
                }
                for r in rows if r["batch_id"]
            ]

    async def count_batches(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT COUNT(DISTINCT batch_id) FROM custom_notifications WHERE batch_id <> ''")
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def unacked_in_batch(self, batch_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT cn.id, u.tg_id, cn.user_id FROM custom_notifications cn JOIN users u ON u.id=cn.user_id "
                "WHERE cn.batch_id=? AND cn.acknowledged=0",
                (batch_id,)
            )
            return [
                {"notif_id": r["id"], "tg_id": r["tg_id"], "user_id": r["user_id"]}
                for r in await cur.fetchall()
            ]

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
