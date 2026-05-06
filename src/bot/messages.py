from __future__ import annotations

from src.config import DAYS_OF_WEEK, PRODUCT_CATALOG
from src.db.models import Order, ProductPrice, Schedule
from src.scraper.amul_scraper import ScrapedProduct


def welcome_message() -> str:
    return (
        "*Welcome to Amul Protein Bot!*\n\n"
        "I help you track and order Amul High Protein products "
        "from shop.amul.com.\n\n"
        "*Commands:*\n"
        "/products - View products with live prices\n"
        "/track - Availability dashboard & watchlist\n"
        "/order - Start a new order\n"
        "/schedule - Set up weekly order reminders\n"
        "/myorders - View order history\n"
        "/settings - Configure pincode & notifications\n"
        "/help - Show this help message\n\n"
        "Get started by checking /products or /track availability!"
    )


def help_message() -> str:
    return (
        "*Amul Protein Bot - Help*\n\n"
        "/start - Welcome & setup\n"
        "/products - Show all products with prices & availability\n"
        "/track - Availability dashboard & stock watchlist\n"
        "/order - Select products & quantities, prepare cart\n"
        "/schedule - Configure weekly order reminders\n"
        "/myorders - View your recent orders\n"
        "/settings - Set pincode, toggle notifications\n"
        "/help - This help message\n\n"
        "_Tip: Use /track to watch out-of-stock items. "
        "You'll get notified the moment they're back!_"
    )


def product_list_message(products: list[ScrapedProduct]) -> str:
    if not products:
        return (
            "*Amul High Protein Products*\n\n"
            "Could not fetch product data right now.\n"
            "Try again in a few minutes with /products"
        )

    lines = ["*Amul High Protein Products*\n"]
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

    lines.append("\nUse /order to place an order!")
    return "\n".join(lines)


def product_list_from_db(prices: list[ProductPrice]) -> str:
    if not prices:
        return (
            "*Amul High Protein Products*\n\n"
            "No cached data yet. Fetching fresh prices..."
        )

    lines = ["*Amul High Protein Products*\n"]
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

    lines.append("\nUse /order to place an order!")
    return "\n".join(lines)


def order_summary_message(
    items: dict[str, int], prices: dict[str, float]
) -> str:
    lines = ["*Order Summary*\n"]
    total = 0.0
    for pid, qty in items.items():
        product = PRODUCT_CATALOG.get(pid)
        if not product:
            continue
        price = prices.get(pid, 0.0)
        line_total = price * qty
        total += line_total
        price_str = f"Rs. {price:.0f}" if price > 0 else "Price N/A"
        lines.append(f"  {product.short_name} x{qty} - {price_str}")

    if total > 0:
        lines.append(f"\n*Estimated Total: Rs. {total:.0f}*")
    else:
        lines.append("\n_Prices not available for estimate_")

    lines.append("\nConfirm to prepare your cart on shop.amul.com")
    return "\n".join(lines)


def cart_ready_message(checkout_url: str, errors: list[str]) -> str:
    lines = []
    if errors:
        lines.append("*Some items had issues:*")
        for err in errors:
            lines.append(f"  - {err}")
        lines.append("")

    lines.append("*Your cart is ready!*\n")
    lines.append(f"Complete your order here:\n{checkout_url}\n")
    lines.append(
        "_Open the link in your browser to login and complete payment._"
    )
    return "\n".join(lines)


def cart_fallback_message(
    links: list[tuple[str, str, int]]
) -> str:
    lines = [
        "*Could not auto-add to cart.*\n",
        "Please add items manually using these links:\n",
    ]
    for name, url, qty in links:
        lines.append(f"  [{name} x{qty}]({url})")
    return "\n".join(lines)


def order_history_message(orders: list[Order]) -> str:
    if not orders:
        return "*Order History*\n\nNo orders yet. Use /order to place one!"

    lines = ["*Recent Orders*\n"]
    for o in orders:
        product_names = []
        for pid, qty in o.products.items():
            product = PRODUCT_CATALOG.get(pid)
            name = product.short_name if product else pid
            product_names.append(f"{name} x{qty}")

        status_emoji = {
            "pending": "[...]",
            "cart_ready": "[Cart]",
            "completed": "[Done]",
            "failed": "[Fail]",
            "skipped": "[Skip]",
        }.get(o.status, f"[{o.status}]")

        items_str = ", ".join(product_names)
        total_str = f" | Rs. {o.total_estimate:.0f}" if o.total_estimate > 0 else ""
        lines.append(
            f"{status_emoji} #{o.id} - {items_str}{total_str}\n"
            f"  {o.created_at[:16]}"
        )
        if o.checkout_url:
            lines.append(f"  [Open Cart]({o.checkout_url})")
        lines.append("")

    return "\n".join(lines)


def schedule_info_message(schedules: list[Schedule]) -> str:
    if not schedules:
        return (
            "*Your Schedules*\n\n"
            "No schedules set. Tap *+ New Schedule* below to create one!"
        )

    lines = ["*Your Schedules*\n"]
    for s in schedules:
        day = DAYS_OF_WEEK[s.day_of_week]
        status = "Active" if s.active else "Paused"
        product_names = []
        for pid, qty in s.products.items():
            product = PRODUCT_CATALOG.get(pid)
            name = product.short_name if product else pid
            product_names.append(f"{name} x{qty}")
        items_str = ", ".join(product_names) if product_names else "All products"
        lines.append(
            f"*{day} at {s.hour:02d}:{s.minute:02d}* [{status}]\n"
            f"  Items: {items_str}\n"
        )

    lines.append("Tap a schedule to toggle, or add a new one.")
    return "\n".join(lines)


def reminder_message(schedule: Schedule, prices: dict[str, float]) -> str:
    day = DAYS_OF_WEEK[schedule.day_of_week]
    lines = [f"*Weekly Order Reminder - {day}*\n"]

    total = 0.0
    for pid, qty in schedule.products.items():
        product = PRODUCT_CATALOG.get(pid)
        if not product:
            continue
        price = prices.get(pid, 0.0)
        line_total = price * qty
        total += line_total
        price_str = f"Rs. {price:.0f}" if price > 0 else "Price N/A"
        lines.append(f"  {product.short_name} x{qty} - {price_str}")

    if total > 0:
        lines.append(f"\n*Estimated Total: Rs. {total:.0f}*")

    lines.append("\nTap *Order Now* to prepare your cart!")
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

    # Group by category
    rtd = []
    kool = []
    whey = []
    other = []
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

    lines.append("\nTap *(+) Watch* to get notified when an out-of-stock item returns.")
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
        lines.append(f"\n[Order Now]({url})")
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
