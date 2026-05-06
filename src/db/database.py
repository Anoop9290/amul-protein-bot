from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from src.config import DB_PATH
from src.db.models import ProductPrice, User

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id   INTEGER PRIMARY KEY,
    pincode       TEXT DEFAULT '',
    notifications_enabled INTEGER DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product_prices (
    product_id    TEXT PRIMARY KEY,
    price         REAL DEFAULT 0.0,
    in_stock      INTEGER DEFAULT 1,
    pack_info     TEXT DEFAULT '',
    last_checked  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    product_id    TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    notified      INTEGER DEFAULT 0,
    UNIQUE(user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: Path | str | None = None):
        self._path = str(db_path or DB_PATH)

    async def init(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()
        logger.info("Database initialized at %s", self._path)

    # ── Users ──

    async def upsert_user(self, telegram_id: int, pincode: str = "") -> User:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                """INSERT INTO users (telegram_id, pincode, created_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(telegram_id) DO UPDATE SET
                       pincode = CASE WHEN excluded.pincode != '' THEN excluded.pincode ELSE users.pincode END
                """,
                (telegram_id, pincode, _now()),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cursor.fetchone()
            return User.from_row(row)

    async def get_user(self, telegram_id: int) -> User | None:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cursor.fetchone()
            return User.from_row(row) if row else None

    async def update_user_pincode(self, telegram_id: int, pincode: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "UPDATE users SET pincode = ? WHERE telegram_id = ?",
                (pincode, telegram_id),
            )
            await db.commit()

    async def update_user_notifications(
        self, telegram_id: int, enabled: bool
    ) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "UPDATE users SET notifications_enabled = ? WHERE telegram_id = ?",
                (int(enabled), telegram_id),
            )
            await db.commit()

    # ── Product Prices ──

    async def upsert_product_price(
        self,
        product_id: str,
        price: float,
        in_stock: bool,
        pack_info: str = "",
    ) -> ProductPrice:
        now = _now()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """INSERT INTO product_prices (product_id, price, in_stock, pack_info, last_checked)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(product_id) DO UPDATE SET
                       price = excluded.price,
                       in_stock = excluded.in_stock,
                       pack_info = excluded.pack_info,
                       last_checked = excluded.last_checked
                """,
                (product_id, price, int(in_stock), pack_info, now),
            )
            await db.commit()
            return ProductPrice(
                product_id=product_id,
                price=price,
                in_stock=in_stock,
                last_checked=now,
                pack_info=pack_info,
            )

    async def get_product_price(self, product_id: str) -> ProductPrice | None:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM product_prices WHERE product_id = ?", (product_id,)
            )
            row = await cursor.fetchone()
            return ProductPrice.from_row(row) if row else None

    async def get_all_product_prices(self) -> list[ProductPrice]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM product_prices")
            rows = await cursor.fetchall()
            return [ProductPrice.from_row(r) for r in rows]

    # ── Watchlist ──

    async def add_to_watchlist(self, user_id: int, product_id: str) -> bool:
        async with aiosqlite.connect(self._path) as db:
            try:
                await db.execute(
                    """INSERT INTO watchlist (user_id, product_id, created_at, notified)
                       VALUES (?, ?, ?, 0)""",
                    (user_id, product_id, _now()),
                )
                await db.commit()
                return True
            except Exception:
                return False

    async def remove_from_watchlist(self, user_id: int, product_id: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "DELETE FROM watchlist WHERE user_id = ? AND product_id = ?",
                (user_id, product_id),
            )
            await db.commit()

    async def get_user_watchlist(self, user_id: int) -> list[str]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT product_id FROM watchlist WHERE user_id = ? AND notified = 0",
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [row["product_id"] for row in rows]

    async def get_watchers_for_product(self, product_id: str) -> list[int]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id FROM watchlist WHERE product_id = ? AND notified = 0",
                (product_id,),
            )
            rows = await cursor.fetchall()
            return [row["user_id"] for row in rows]

    async def mark_watchlist_notified(self, user_id: int, product_id: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "UPDATE watchlist SET notified = 1 WHERE user_id = ? AND product_id = ?",
                (user_id, product_id),
            )
            await db.commit()

    async def clear_user_watchlist(self, user_id: int) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "DELETE FROM watchlist WHERE user_id = ?", (user_id,)
            )
            await db.commit()
