from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.config import ADMIN_USER_ID, PRODUCT_CATALOG
from src.bot import keyboards, messages
from src.db.database import Database
from src.scraper.amul_scraper import AmulScraper

logger = logging.getLogger(__name__)

PINCODE_INPUT = 20


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    if ADMIN_USER_ID == 0:
        return True
    return user is not None and user.id == ADMIN_USER_ID


def _get_db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.bot_data["db"]


def _get_scraper(context: ContextTypes.DEFAULT_TYPE) -> AmulScraper:
    return context.bot_data["scraper"]


# ── /start ──


async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not _is_admin(update):
        return
    db = _get_db(context)
    user = update.effective_user
    assert user is not None
    await db.upsert_user(user.id)
    await update.message.reply_text(
        messages.welcome_message(), parse_mode=ParseMode.MARKDOWN
    )


# ── /help ──


async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not _is_admin(update):
        return
    await update.message.reply_text(
        messages.help_message(), parse_mode=ParseMode.MARKDOWN
    )


# ── /products ──


async def products_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not _is_admin(update):
        return

    msg = await update.message.reply_text("Fetching product data...")

    db = _get_db(context)
    scraper = _get_scraper(context)

    try:
        scraped = await scraper.scrape_all()
        for sp in scraped:
            await db.upsert_product_price(
                sp.product_id, sp.price, sp.in_stock, sp.pack_info
            )
        text = messages.product_list_message(scraped)
    except Exception as exc:
        logger.error("Failed to scrape products: %s", exc)
        prices = await db.get_all_product_prices()
        text = messages.product_list_from_db(prices)

    await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)


# ── /track ──


async def track_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not _is_admin(update):
        return

    db = _get_db(context)
    user = update.effective_user
    assert user is not None

    prices_list = await db.get_all_product_prices()
    stock_status = {pp.product_id: pp.in_stock for pp in prices_list}
    last_checked = max((pp.last_checked for pp in prices_list), default="")

    watchlist = set(await db.get_user_watchlist(user.id))

    text = messages.track_dashboard_message(stock_status, watchlist, last_checked)
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboards.track_keyboard(watchlist, stock_status),
    )


async def track_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    db = _get_db(context)
    user = update.effective_user
    assert user is not None

    if data.startswith("track_toggle:"):
        pid = data.split(":", 1)[1]
        current_watchlist = await db.get_user_watchlist(user.id)
        if pid in current_watchlist:
            await db.remove_from_watchlist(user.id, pid)
        else:
            await db.add_to_watchlist(user.id, pid)

    elif data == "track_clear":
        await db.clear_user_watchlist(user.id)

    elif data == "track_refresh":
        scraper = _get_scraper(context)
        try:
            await query.edit_message_text("Refreshing availability data...")
            scraped = await scraper.scrape_all()
            for sp in scraped:
                await db.upsert_product_price(
                    sp.product_id, sp.price, sp.in_stock, sp.pack_info
                )
        except Exception as exc:
            logger.error("Track refresh failed: %s", exc)

    elif data.startswith("track_info:"):
        pid = data.split(":", 1)[1]
        product = PRODUCT_CATALOG.get(pid)
        if product:
            pp = await db.get_product_price(pid)
            price_str = f"Rs. {pp.price:.0f}" if pp and pp.price > 0 else "N/A"
            stock = "In Stock" if pp and pp.in_stock else "Out of Stock"
            checked = pp.last_checked[:16] if pp else "Never"
            await query.answer(
                f"{product.name}\n{price_str} | {stock}\nChecked: {checked}",
                show_alert=True,
            )
            return

    # Refresh dashboard
    prices_list = await db.get_all_product_prices()
    stock_status = {pp.product_id: pp.in_stock for pp in prices_list}
    last_checked = max((pp.last_checked for pp in prices_list), default="")
    watchlist = set(await db.get_user_watchlist(user.id))

    text = messages.track_dashboard_message(stock_status, watchlist, last_checked)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboards.track_keyboard(watchlist, stock_status),
    )


# ── /settings ──


async def settings_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not _is_admin(update):
        return ConversationHandler.END

    db = _get_db(context)
    user = update.effective_user
    assert user is not None
    db_user = await db.get_user(user.id)

    if not db_user:
        await db.upsert_user(user.id)
        db_user = await db.get_user(user.id)

    text = messages.settings_message(
        db_user.pincode if db_user else "",
        db_user.notifications_enabled if db_user else True,
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboards.settings_keyboard(
            db_user.notifications_enabled if db_user else True
        ),
    )
    return PINCODE_INPUT


async def settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    db = _get_db(context)
    user = update.effective_user
    assert user is not None

    if data == "settings:pincode":
        await query.edit_message_text("Send me your 6-digit delivery pincode:")
        return PINCODE_INPUT

    if data == "settings:toggle_notif":
        db_user = await db.get_user(user.id)
        if db_user:
            new_val = not db_user.notifications_enabled
            await db.update_user_notifications(user.id, new_val)
            text = messages.settings_message(db_user.pincode, new_val)
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboards.settings_keyboard(new_val),
            )
        return PINCODE_INPUT

    return PINCODE_INPUT


async def pincode_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or len(text) != 6:
        await update.message.reply_text("Please enter a valid 6-digit pincode:")
        return PINCODE_INPUT

    db = _get_db(context)
    user = update.effective_user
    assert user is not None
    await db.update_user_pincode(user.id, text)
    await update.message.reply_text(
        f"Pincode updated to *{text}*.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def settings_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    return ConversationHandler.END


# ── Handler Registration ──


def get_all_handlers() -> list:
    settings_conv = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_command)],
        states={
            PINCODE_INPUT: [
                CallbackQueryHandler(settings_callback, pattern=r"^settings:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, pincode_input),
            ],
        },
        fallbacks=[CommandHandler("cancel", settings_cancel)],
    )

    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("products", products_command),
        CommandHandler("track", track_command),
        settings_conv,
        CallbackQueryHandler(track_callback, pattern=r"^track_"),
    ]
