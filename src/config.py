from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=False)  # don't override OS-level env vars (e.g. Railway)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "amul_bot.db"

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_USER_ID: int = int(os.getenv("ADMIN_USER_ID", "0"))
DEFAULT_PINCODE: str = os.getenv("DEFAULT_PINCODE", "380001")
PRICE_CHECK_INTERVAL_HOURS: int = int(os.getenv("PRICE_CHECK_INTERVAL_HOURS", "6"))
SCRAPE_CACHE_TTL_MINUTES: int = int(os.getenv("SCRAPE_CACHE_TTL_MINUTES", "30"))

SHOP_BASE_URL = "https://shop.amul.com"


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    short_name: str
    url: str
    pack_info: str
    protein: str
    default_qty: int = 1
    tags: list[str] = field(default_factory=list)


PRODUCT_CATALOG: dict[str, Product] = {
    p.id: p
    for p in [
        Product(
            id="hp_buttermilk",
            name="Amul High Protein Buttermilk",
            short_name="HP Buttermilk",
            url="https://shop.amul.com/en/product/amul-high-protein-buttermilk-200-ml-or-pack-of-30",
            pack_info="200ml x 30",
            protein="15g per 200ml",
            default_qty=1,
            tags=["buttermilk", "protein"],
        ),
        Product(
            id="hp_milk",
            name="Amul High Protein Milk",
            short_name="HP Milk",
            url="https://shop.amul.com/en/product/amul-high-protein-milk-250-ml-or-pack-of-32",
            pack_info="250ml x 32",
            protein="35g per 250ml",
            default_qty=1,
            tags=["milk", "protein"],
        ),
        Product(
            id="hp_lassi",
            name="Amul High Protein Lassi",
            short_name="HP Lassi",
            url="https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30",
            pack_info="200ml x 30",
            protein="15g per 200ml",
            default_qty=1,
            tags=["lassi", "protein"],
        ),
        Product(
            id="hp_rose_lassi",
            name="Amul High Protein Rose Lassi",
            short_name="HP Rose Lassi",
            url="https://shop.amul.com/en/product/amul-high-protein-rose-lassi-200-ml-or-pack-of-30",
            pack_info="200ml x 30",
            protein="15g per 200ml",
            default_qty=1,
            tags=["lassi", "rose", "protein"],
        ),
        Product(
            id="hp_blueberry_shake",
            name="Amul High Protein Blueberry Shake",
            short_name="HP Blueberry Shake",
            url="https://shop.amul.com/en/product/amul-high-protein-blueberry-shake-200-ml-or-pack-of-30",
            pack_info="200ml x 30",
            protein="15g per 200ml",
            default_qty=1,
            tags=["shake", "blueberry", "protein"],
        ),
    ]
}

DAYS_OF_WEEK = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

HOUR_SLOTS = [f"{h:02d}:00" for h in range(6, 23)]
