from __future__ import annotations

from dataclasses import dataclass


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
    def from_row(cls, row) -> ProductPrice:
        try:
            pack_info = row["pack_info"]
        except (IndexError, KeyError):
            pack_info = ""
        return cls(
            product_id=row["product_id"],
            price=row["price"],
            in_stock=bool(row["in_stock"]),
            last_checked=row["last_checked"],
            pack_info=pack_info or "",
        )
