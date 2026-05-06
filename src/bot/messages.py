from __future__ import annotations

from src.config import PRODUCT_CATALOG
from src.db.models import ProductPrice
from src.scraper.amul_scraper import ScrapedProduct


def welcome_message() -> str:
    return (
        "*Welcome to Amul Protein Tracker!*\n\n"
        "I track availability and prices of all Amul High Protein "
        "products on shop.amul.com.\n\n"
        "*Commands:*\n"
        "/products - View all products with live prices\n"
        "/track - Availability dashboard & watchlist\n"
        "/settings - Configure notifications\n"
        "/help - Show this help message\n\n"
        "Start with /track to see what's in stock!"
    )


def help_message() -> str:
    return (
        "*Amul Protein Tracker - Help*\n\n"
        "/start - Welcome & setup\n"
        "/products - Fetch live prices & stock for all products\n"
        "/track - Availability dashboard with watch/unwatch\n"
        "/settings - Toggle notifications on/off\n"
        "/help - This help message\n\n"
        "*How tracking works:*\n"
        "1. Use /track to see stock status of all 13 products\n"
        "2. Tap *(+) Watch* on any out-of-stock item\n"
        "3. Bot checks every 6 hours automatically\n"
        "4. You get an instant alert when it's back in stock!\n\n"
        "_Tap product name for price & last-checked details._"
    )


def product_list_message(products: list[ScrapedProduct]) -> str:
    if not products:
        return (
            "*Amul High Protein Products*\n\n"
            "Could not fetch product data right now.\n"
            "Try again in a few minutes with /products"
        )

    in_stock = sum(1 for p in products if p.in_stock)
    lines = [f"*Amul High Protein Products* ({in_stock}/{len(products)} in stock)\n"]

    for p in products:
        catalog_entry = PRODUCT_CATALOG.get(p.product_id)
        protein_info = catalog_entry.protein if catalog_entry else ""

        stock = "In Stock" if p.in_stock else "Out of Stock"
        price_str = f"Rs. {p.price:.0f}" if p.price > 0 else "Price N/A"

        lines.append(
            f"*{p.name}*\n"
            f"  {p.pack_info} | {protein_info}\n"
            f"  {price_str} | {stock}\n"
        )

    return "\n".join(lines)


def product_list_from_db(prices: list[ProductPrice]) -> str:
    if not prices:
        return (
            "*Amul High Protein Products*\n\n"
            "No cached data yet. Fetching fresh prices..."
        )

    in_stock = sum(1 for pp in prices if pp.in_stock)
    lines = [f"*Amul High Protein Products* ({in_stock}/{len(prices)} in stock)\n"]

    for pp in prices:
        catalog_entry = PRODUCT_CATALOG.get(pp.product_id)
        if not catalog_entry:
            continue
        stock = "In Stock" if pp.in_stock else "Out of Stock"
        price_str = f"Rs. {pp.price:.0f}" if pp.price > 0 else "Price N/A"
        lines.append(
            f"*{catalog_entry.name}*\n"
            f"  {catalog_entry.pack_info} | {catalog_entry.protein}\n"
            f"  {price_str} | {stock}\n"
        )

    return "\n".join(lines)


def track_dashboard_message(
    stock_status: dict[str, bool],
    watchlist: set[str],
    last_checked: str,
) -> str:
    in_count = sum(1 for v in stock_status.values() if v is True)
    out_count = sum(1 for v in stock_status.values() if v is False)
    unknown = len(PRODUCT_CATALOG) - in_count - out_count

    lines = [
        "*Availability Tracker*\n",
        f"In Stock: {in_count} | Out of Stock: {out_count}"
        + (f" | Unknown: {unknown}" if unknown else ""),
        f"Watching: {len(watchlist)} products\n",
    ]

    rtd, kool, whey, other = [], [], [], []
    for pid, product in PRODUCT_CATALOG.items():
        status = stock_status.get(pid)
        icon = "[OK]" if status is True else "[X]" if status is False else "[?]"
        watch = " (watching)" if pid in watchlist else ""
        entry = f"{icon} {product.short_name}{watch}"

        if "kool" in product.tags:
            kool.append(entry)
        elif "whey" in product.tags:
            whey.append(entry)
        elif "rtd" in product.tags:
            rtd.append(entry)
        else:
            other.append(entry)

    if rtd:
        lines.append("*Ready-to-Drink:*")
        lines.extend(f"  {e}" for e in rtd)
    if kool:
        lines.append("*Kool Milkshakes:*")
        lines.extend(f"  {e}" for e in kool)
    if whey:
        lines.append("*Whey Protein:*")
        lines.extend(f"  {e}" for e in whey)
    if other:
        lines.append("*Other:*")
        lines.extend(f"  {e}" for e in other)

    if last_checked:
        lines.append(f"\n_Last checked: {last_checked[:16]} UTC_")

    lines.append("\nTap *(+) Watch* to get notified when an item returns.")
    return "\n".join(lines)


def back_in_stock_alert(product_id: str, price: float) -> str:
    product = PRODUCT_CATALOG.get(product_id)
    name = product.name if product else product_id
    price_str = f"Rs. {price:.0f}" if price > 0 else ""
    url = product.url if product else ""

    lines = [
        "*Back in Stock!*\n",
        f"*{name}* is now available!",
    ]
    if price_str:
        lines.append(f"Price: {price_str}")
    if url:
        lines.append(f"\n[Buy on shop.amul.com]({url})")
    return "\n".join(lines)


def price_alert_message(
    changes: list[tuple[str, float, float]],
    stock_changes: list[tuple[str, bool]],
) -> str:
    lines = ["*Price/Stock Alert*\n"]

    if changes:
        lines.append("*Price Changes:*")
        for pid, old_price, new_price in changes:
            product = PRODUCT_CATALOG.get(pid)
            name = product.short_name if product else pid
            direction = "UP" if new_price > old_price else "DOWN"
            lines.append(
                f"  {name}: Rs. {old_price:.0f} -> Rs. {new_price:.0f} ({direction})"
            )
        lines.append("")

    if stock_changes:
        lines.append("*Stock Changes:*")
        for pid, now_in_stock in stock_changes:
            product = PRODUCT_CATALOG.get(pid)
            name = product.short_name if product else pid
            status = "Back in Stock!" if now_in_stock else "Out of Stock"
            lines.append(f"  {name}: {status}")

    return "\n".join(lines)


def settings_message(pincode: str, notifications_on: bool) -> str:
    notif = "Enabled" if notifications_on else "Disabled"
    pin = pincode if pincode else "Not set"
    return (
        "*Settings*\n\n"
        f"*Pincode:* {pin}\n"
        f"*Notifications:* {notif}\n\n"
        "Tap below to change settings."
    )
