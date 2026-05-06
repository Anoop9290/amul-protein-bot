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
        # ── Ready-to-Drink High Protein ──
        Product(
            id="hp_buttermilk",
            name="Amul High Protein Buttermilk",
            short_name="HP Buttermilk",
            url="https://shop.amul.com/en/product/amul-high-protein-buttermilk-200-ml-or-pack-of-30",
            pack_info="200ml x 30",
            protein="15g per 200ml",
            default_qty=1,
            tags=["buttermilk", "protein", "rtd"],
        ),
        Product(
            id="hp_milk",
            name="Amul High Protein Milk",
            short_name="HP Milk",
            url="https://shop.amul.com/en/product/amul-high-protein-milk-250-ml-or-pack-of-32",
            pack_info="250ml x 32",
            protein="35g per 250ml",
            default_qty=1,
            tags=["milk", "protein", "rtd"],
        ),
        Product(
            id="hp_lassi",
            name="Amul High Protein Lassi Plain",
            short_name="HP Lassi",
            url="https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30",
            pack_info="200ml x 30",
            protein="15g per 200ml",
            default_qty=1,
            tags=["lassi", "protein", "rtd"],
        ),
        Product(
            id="hp_rose_lassi",
            name="Amul High Protein Rose Lassi",
            short_name="HP Rose Lassi",
            url="https://shop.amul.com/en/product/amul-high-protein-rose-lassi-200-ml-or-pack-of-30",
            pack_info="200ml x 30",
            protein="15g per 200ml",
            default_qty=1,
            tags=["lassi", "rose", "protein", "rtd"],
        ),
        Product(
            id="hp_blueberry_shake",
            name="Amul High Protein Blueberry Shake",
            short_name="HP Blueberry Shake",
            url="https://shop.amul.com/en/product/amul-high-protein-blueberry-shake-200-ml-or-pack-of-30",
            pack_info="200ml x 30",
            protein="15g per 200ml",
            default_qty=1,
            tags=["shake", "blueberry", "protein", "rtd"],
        ),
        # ── Kool Protein Milkshakes ──
        Product(
            id="hp_kool_kesar",
            name="Amul Kool Protein Milkshake Kesar",
            short_name="Kool Kesar",
            url="https://shop.amul.com/en/product/amul-kool-protein-milkshake-or-kesar-180-ml-or-pack-of-30",
            pack_info="180ml x 30",
            protein="10g per 180ml",
            default_qty=1,
            tags=["kool", "kesar", "milkshake", "protein", "rtd"],
        ),
        Product(
            id="hp_kool_coffee",
            name="Amul Kool Protein Milkshake Coffee",
            short_name="Kool Coffee",
            url="https://shop.amul.com/en/product/amul-kool-protein-milkshake-or-arabica-coffee-180-ml-or-pack-of-30",
            pack_info="180ml x 30",
            protein="10g per 180ml",
            default_qty=1,
            tags=["kool", "coffee", "milkshake", "protein", "rtd"],
        ),
        Product(
            id="hp_kool_chocolate",
            name="Amul Kool Protein Milkshake Chocolate",
            short_name="Kool Chocolate",
            url="https://shop.amul.com/en/product/amul-kool-protein-milkshake-or-chocolate-180-ml-or-pack-of-30",
            pack_info="180ml x 30",
            protein="10g per 180ml",
            default_qty=1,
            tags=["kool", "chocolate", "milkshake", "protein", "rtd"],
        ),
        # ── Whey Protein Powder ──
        Product(
            id="whey_plain_sachet",
            name="Amul Whey Protein Plain Sachets",
            short_name="Whey Plain (60s)",
            url="https://shop.amul.com/en/product/amul-whey-protein-32-g-or-pack-of-60-sachet",
            pack_info="32g x 60 sachets",
            protein="25g per sachet",
            default_qty=1,
            tags=["whey", "plain", "powder", "protein"],
        ),
        Product(
            id="whey_chocolate_sachet",
            name="Amul Whey Protein Chocolate Sachets",
            short_name="Whey Chocolate (30s)",
            url="https://shop.amul.com/en/product/amul-whey-protein-chocolate-34-g-or-pack-of-30-sachet",
            pack_info="34g x 30 sachets",
            protein="25g per sachet",
            default_qty=1,
            tags=["whey", "chocolate", "powder", "protein"],
        ),
        Product(
            id="whey_plain_1kg",
            name="Amul Whey Protein Plain 1kg",
            short_name="Whey Plain 1kg",
            url="https://shop.amul.com/en/product/amul-whey-protein-1x1-92-kg",
            pack_info="1.92 kg",
            protein="25g per 32g serving",
            default_qty=1,
            tags=["whey", "plain", "powder", "protein", "bulk"],
        ),
        Product(
            id="whey_chocolate_1kg",
            name="Amul Whey Protein Chocolate 1kg",
            short_name="Whey Choco 1kg",
            url="https://shop.amul.com/en/product/amul-whey-protein-chocolate-1x1-02-kg",
            pack_info="1.02 kg",
            protein="25g per 34g serving",
            default_qty=1,
            tags=["whey", "chocolate", "powder", "protein", "bulk"],
        ),
        # ── High Protein Paneer ──
        Product(
            id="hp_paneer",
            name="Amul High Protein Paneer",
            short_name="HP Paneer",
            url="https://shop.amul.com/en/product/amul-high-protein-paneer-200-g",
            pack_info="200g",
            protein="32g per 200g",
            default_qty=1,
            tags=["paneer", "protein"],
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
