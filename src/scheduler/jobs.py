from __future__ import annotations

import logging

from telegram.constants import ParseMode
from telegram.ext import Application

from src.config import ADMIN_USER_ID
from src.bot import messages
from src.db.database import Database
from src.scraper.amul_scraper import AmulScraper

logger = logging.getLogger(__name__)


async def price_check_job(app: Application) -> None:
    """Periodically scrape all products and alert on price/stock changes."""
    db: Database = app.bot_data["db"]
    scraper: AmulScraper = app.bot_data["scraper"]

    logger.info("Running scheduled price check")

    old_prices = await db.get_all_product_prices()
    old_map = {pp.product_id: pp for pp in old_prices}

    try:
        scraped = await scraper.scrape_all()
    except Exception as exc:
        logger.error("Price check scrape failed: %s", exc)
        return

    price_changes: list[tuple[str, float, float]] = []
    stock_changes: list[tuple[str, bool]] = []

    for sp in scraped:
        old = old_map.get(sp.product_id)

        await db.upsert_product_price(
            sp.product_id, sp.price, sp.in_stock, sp.pack_info
        )

        if old:
            if old.price > 0 and sp.price > 0 and abs(old.price - sp.price) > 1:
                price_changes.append((sp.product_id, old.price, sp.price))
            if old.in_stock != sp.in_stock:
                stock_changes.append((sp.product_id, sp.in_stock))

    # Send price/stock alert to admin
    if (price_changes or stock_changes) and ADMIN_USER_ID:
        user = await db.get_user(ADMIN_USER_ID)
        if user and user.notifications_enabled:
            text = messages.price_alert_message(price_changes, stock_changes)
            try:
                await app.bot.send_message(
                    chat_id=ADMIN_USER_ID,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as exc:
                logger.error("Failed to send price alert: %s", exc)

    # Notify watchers when out-of-stock items come back
    for product_id, now_in_stock in stock_changes:
        if not now_in_stock:
            continue
        watchers = await db.get_watchers_for_product(product_id)
        sp_data = next((s for s in scraped if s.product_id == product_id), None)
        price = sp_data.price if sp_data else 0.0

        for watcher_id in watchers:
            watcher = await db.get_user(watcher_id)
            if not watcher or not watcher.notifications_enabled:
                continue
            try:
                text = messages.back_in_stock_alert(product_id, price)
                await app.bot.send_message(
                    chat_id=watcher_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=False,
                )
                await db.mark_watchlist_notified(watcher_id, product_id)
                logger.info(
                    "Sent back-in-stock alert for %s to user %d",
                    product_id,
                    watcher_id,
                )
            except Exception as exc:
                logger.error("Failed to send watchlist alert: %s", exc)

    logger.info(
        "Price check done: %d price changes, %d stock changes",
        len(price_changes),
        len(stock_changes),
    )


def register_jobs(app: Application) -> None:
    """Register all scheduled jobs with the application's job queue."""
    from src.config import PRICE_CHECK_INTERVAL_HOURS

    job_queue = app.job_queue
    if job_queue is None:
        logger.warning("Job queue not available; scheduled jobs disabled")
        return

    job_queue.run_repeating(
        lambda ctx: price_check_job(ctx.application),
        interval=PRICE_CHECK_INTERVAL_HOURS * 3600,
        first=30,
        name="price_check",
    )

    logger.info(
        "Registered jobs: price_check (every %dh)",
        PRICE_CHECK_INTERVAL_HOURS,
    )
