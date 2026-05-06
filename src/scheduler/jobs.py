from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram.constants import ParseMode
from telegram.ext import Application

from src.config import ADMIN_USER_ID, PRODUCT_CATALOG
from src.bot import keyboards, messages
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

    logger.info(
        "Price check done: %d price changes, %d stock changes",
        len(price_changes),
        len(stock_changes),
    )


async def schedule_reminder_job(app: Application) -> None:
    """Check for schedules matching current time and send reminders."""
    db: Database = app.bot_data["db"]

    now = datetime.now(timezone.utc)
    day = now.weekday()  # 0=Monday
    hour = now.hour
    minute = now.minute

    # Match schedules within a 5-minute window
    schedules = await db.get_active_schedules_for_time(day, hour, minute)

    if not schedules:
        return

    logger.info("Found %d schedules for %s %02d:%02d", len(schedules), day, hour, minute)

    prices_list = await db.get_all_product_prices()
    price_map = {pp.product_id: pp.price for pp in prices_list}

    for schedule in schedules:
        user = await db.get_user(schedule.user_id)
        if not user or not user.notifications_enabled:
            continue

        if not schedule.products:
            schedule.products = {pid: 1 for pid in PRODUCT_CATALOG}

        text = messages.reminder_message(schedule, price_map)

        try:
            await app.bot.send_message(
                chat_id=schedule.user_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboards.reminder_action_keyboard(schedule.id),
            )
            logger.info("Sent reminder for schedule #%d to user %d", schedule.id, schedule.user_id)
        except Exception as exc:
            logger.error("Failed to send reminder for schedule #%d: %s", schedule.id, exc)


def register_jobs(app: Application) -> None:
    """Register all scheduled jobs with the application's job queue."""
    from src.config import PRICE_CHECK_INTERVAL_HOURS

    job_queue = app.job_queue
    if job_queue is None:
        logger.warning("Job queue not available; scheduled jobs disabled")
        return

    # Price check every N hours
    job_queue.run_repeating(
        lambda ctx: price_check_job(ctx.application),
        interval=PRICE_CHECK_INTERVAL_HOURS * 3600,
        first=30,  # first run 30s after startup
        name="price_check",
    )

    # Schedule reminder check every minute
    job_queue.run_repeating(
        lambda ctx: schedule_reminder_job(ctx.application),
        interval=60,
        first=10,
        name="schedule_reminder",
    )

    logger.info(
        "Registered jobs: price_check (every %dh), schedule_reminder (every 1m)",
        PRICE_CHECK_INTERVAL_HOURS,
    )
