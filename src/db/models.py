from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    telegram_id: int
    pincode: str = ""
    notifications_enabled: bool = True
    created_at: str = ""

    @classmethod
    def from_row(cls, row: dict) -> User:
        return cls(
            telegram_id=row["telegram_id"],
            pincode=row["pincode"] or "",
            notifications_enabled=bool(row["notifications_enabled"]),
            created_at=row["created_at"],
        )


@dataclass
class ProductPrice:
    product_id: str
    price: float
    in_stock: bool
    last_checked: str
    pack_info: str = ""

    @classmethod
    def from_row(cls, row: dict) -> ProductPrice:
        return cls(
            product_id=row["product_id"],
            price=row["price"],
            in_stock=bool(row["in_stock"]),
            last_checked=row["last_checked"],
            pack_info=row.get("pack_info", ""),
        )


@dataclass
class Schedule:
    id: int
    user_id: int
    day_of_week: int  # 0=Monday .. 6=Sunday
    hour: int
    minute: int
    products: dict[str, int]  # product_id -> quantity
    active: bool = True
    created_at: str = ""

    @classmethod
    def from_row(cls, row: dict) -> Schedule:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            day_of_week=row["day_of_week"],
            hour=row["hour"],
            minute=row["minute"],
            products=json.loads(row["products"]),
            active=bool(row["active"]),
            created_at=row["created_at"],
        )


@dataclass
class Order:
    id: int
    user_id: int
    products: dict[str, int]
    status: str  # pending, cart_ready, completed, failed, skipped
    checkout_url: str = ""
    total_estimate: float = 0.0
    created_at: str = ""

    @classmethod
    def from_row(cls, row: dict) -> Order:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            products=json.loads(row["products"]),
            status=row["status"],
            checkout_url=row["checkout_url"] or "",
            total_estimate=row["total_estimate"],
            created_at=row["created_at"],
        )
