from __future__ import annotations

import logging
from typing import Any

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

from src.config import ADMIN_USER_ID, DAYS_OF_WEEK, PRODUCT_CATALOG
from src.bot import keyboards, messages
from src.db.database import Database
from src.scraper.amul_scraper import AmulScraper
from src.scraper.cart_manager import CartManager

logger = logging.getLogger(__name__)

# Conversation states
SELECT_PRODUCTS, SET_QUANTITIES, CONFIRM_ORDER = range(3)
SCHED_SELECT_PRODUCTS, SCHED_DAY, SCHED_HOUR = range(10, 13)
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


def _get_cart_manager(context: ContextTypes.DEFAULT_TYPE) -> CartManager:
    return context.bot_data["cart_manager"]


# ── Command Handlers ──


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


async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not _is_admin(update):
        return
    await update.message.reply_text(
        messages.help_message(), parse_mode=ParseMode.MARKDOWN
    )


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


async def myorders_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not _is_admin(update):
        return
    db = _get_db(context)
    user = update.effective_user
    assert user is not None
    orders = await db.get_user_orders(user.id)
    text = messages.order_history_message(orders)
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


# ── Order Conversation ──


async def order_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not _is_admin(update):
        return ConversationHandler.END

    context.user_data["selected_products"] = set()
    context.user_data["quantities"] = {}

    db = _get_db(context)
    prices_list = await db.get_all_product_prices()
    stock_status = {pp.product_id: pp.in_stock for pp in prices_list}
    context.user_data["stock_status"] = stock_status

    oos_count = sum(1 for v in stock_status.values() if not v)
    note = f"\n_({oos_count} products out of stock)_" if oos_count else ""

    await update.message.reply_text(
        f"*Select products to order:*\n\nTap to toggle, then press Confirm.{note}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboards.product_selection_keyboard(
            stock_status=stock_status,
        ),
    )
    return SELECT_PRODUCTS


async def order_select_product(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query

    data = query.data
    if not data or not data.startswith("sel_prod:"):
        await query.answer()
        return SELECT_PRODUCTS

    action = data.split(":", 1)[1]
    selected: set[str] = context.user_data.get("selected_products", set())
    stock_status: dict[str, bool] = context.user_data.get("stock_status", {})

    # Out-of-stock item tapped
    if action.startswith("oos:"):
        pid = action.split(":", 1)[1]
        product = PRODUCT_CATALOG.get(pid)
        name = product.short_name if product else pid
        await query.answer(
            f"{name} is out of stock and cannot be ordered.\n"
            f"Use /track to get notified when it's back!",
            show_alert=True,
        )
        return SELECT_PRODUCTS

    if action == "cancel":
        await query.answer()
        await query.edit_message_text("Order cancelled.")
        return ConversationHandler.END

    if action == "all":
        await query.answer()
        in_stock_ids = {
            pid for pid in PRODUCT_CATALOG
            if stock_status.get(pid, True)
        }
        if selected >= in_stock_ids:
            selected.clear()
        else:
            selected = in_stock_ids.copy()
        context.user_data["selected_products"] = selected
        await query.edit_message_reply_markup(
            reply_markup=keyboards.product_selection_keyboard(selected, stock_status)
        )
        return SELECT_PRODUCTS

    if action == "confirm":
        await query.answer()
        if not selected:
            await query.answer("Please select at least one product!", show_alert=True)
            return SELECT_PRODUCTS

        context.user_data["quantities"] = {pid: 1 for pid in selected}
        context.user_data["qty_index"] = 0
        context.user_data["qty_product_ids"] = list(selected)

        return await _show_quantity_step(query, context)

    # Toggle individual product (only if in stock)
    if action in PRODUCT_CATALOG:
        await query.answer()
        if not stock_status.get(action, True):
            await query.answer(
                "This product is out of stock!",
                show_alert=True,
            )
            return SELECT_PRODUCTS
        if action in selected:
            selected.discard(action)
        else:
            selected.add(action)
        context.user_data["selected_products"] = selected

    await query.edit_message_reply_markup(
        reply_markup=keyboards.product_selection_keyboard(selected, stock_status)
    )
    return SELECT_PRODUCTS


async def _show_quantity_step(query: Any, context: ContextTypes.DEFAULT_TYPE) -> int:
    idx = context.user_data.get("qty_index", 0)
    product_ids = context.user_data.get("qty_product_ids", [])
    quantities = context.user_data.get("quantities", {})

    if idx >= len(product_ids):
        return await _show_order_confirm(query, context)

    pid = product_ids[idx]
    product = PRODUCT_CATALOG[pid]
    qty = quantities.get(pid, 1)

    await query.edit_message_text(
        f"*Set quantity for {product.short_name}:*\n"
        f"({product.pack_info})\n\n"
        f"Current: {qty}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboards.quantity_keyboard(pid, qty),
    )
    return SET_QUANTITIES


async def order_set_quantity(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data or not data.startswith("qty:"):
        return SET_QUANTITIES

    parts = data.split(":")
    if len(parts) < 3:
        return SET_QUANTITIES

    pid = parts[1]
    action = parts[2]
    quantities = context.user_data.get("quantities", {})

    if action == "inc":
        quantities[pid] = min(quantities.get(pid, 1) + 1, 10)
        context.user_data["quantities"] = quantities
        product = PRODUCT_CATALOG[pid]
        await query.edit_message_text(
            f"*Set quantity for {product.short_name}:*\n"
            f"({product.pack_info})\n\n"
            f"Current: {quantities[pid]}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboards.quantity_keyboard(pid, quantities[pid]),
        )
        return SET_QUANTITIES

    if action == "dec":
        quantities[pid] = max(quantities.get(pid, 1) - 1, 1)
        context.user_data["quantities"] = quantities
        product = PRODUCT_CATALOG[pid]
        await query.edit_message_text(
            f"*Set quantity for {product.short_name}:*\n"
            f"({product.pack_info})\n\n"
            f"Current: {quantities[pid]}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboards.quantity_keyboard(pid, quantities[pid]),
        )
        return SET_QUANTITIES

    if action == "done":
        context.user_data["qty_index"] = context.user_data.get("qty_index", 0) + 1
        return await _show_quantity_step(query, context)

    return SET_QUANTITIES


async def _show_order_confirm(
    query: Any, context: ContextTypes.DEFAULT_TYPE
) -> int:
    quantities = context.user_data.get("quantities", {})

    db = _get_db(context)
    prices_list = await db.get_all_product_prices()
    prices = {pp.product_id: pp.price for pp in prices_list}

    text = messages.order_summary_message(quantities, prices)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboards.order_confirm_keyboard(),
    )
    return CONFIRM_ORDER


async def order_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data or not data.startswith("order_confirm:"):
        return CONFIRM_ORDER

    action = data.split(":")[1]

    if action.startswith("no"):
        await query.edit_message_text("Order cancelled.")
        return ConversationHandler.END

    # User confirmed — place the order
    quantities = context.user_data.get("quantities", {})
    user = update.effective_user
    assert user is not None

    db = _get_db(context)
    prices_list = await db.get_all_product_prices()
    prices = {pp.product_id: pp.price for pp in prices_list}

    total = sum(
        prices.get(pid, 0.0) * qty for pid, qty in quantities.items()
    )

    order = await db.create_order(
        user_id=user.id,
        products=quantities,
        status="pending",
        total_estimate=total,
    )

    await query.edit_message_text("Preparing your cart on shop.amul.com...")

    cart_mgr = _get_cart_manager(context)
    try:
        checkout_url, errors = await cart_mgr.add_to_cart_and_get_checkout_url(
            quantities
        )
        await db.update_order_status(
            order.id,
            status="cart_ready",
            checkout_url=checkout_url,
            total_estimate=total,
        )
        text = messages.cart_ready_message(checkout_url, errors)
    except Exception as exc:
        logger.error("Cart flow failed: %s", exc)
        links = await cart_mgr.get_direct_cart_links(quantities)
        await db.update_order_status(order.id, status="failed")
        text = messages.cart_fallback_message(links)

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=False,
    )
    return ConversationHandler.END


async def order_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if update.message:
        await update.message.reply_text("Order cancelled.")
    return ConversationHandler.END


# ── Schedule Conversation ──


async def schedule_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int | None:
    if not _is_admin(update):
        return ConversationHandler.END

    db = _get_db(context)
    user = update.effective_user
    assert user is not None
    scheds = await db.get_user_schedules(user.id)

    text = messages.schedule_info_message(scheds)
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboards.schedule_list_keyboard(scheds),
    )
    return SCHED_SELECT_PRODUCTS


async def schedule_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    db = _get_db(context)
    user = update.effective_user
    assert user is not None

    if data.startswith("sched_toggle:"):
        sched_id = int(data.split(":")[1])
        scheds = await db.get_user_schedules(user.id)
        for s in scheds:
            if s.id == sched_id:
                await db.toggle_schedule(sched_id, not s.active)
                break
        scheds = await db.get_user_schedules(user.id)
        text = messages.schedule_info_message(scheds)
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboards.schedule_list_keyboard(scheds),
        )
        return SCHED_SELECT_PRODUCTS

    if data.startswith("sched_del:"):
        sched_id = int(data.split(":")[1])
        await db.delete_schedule(sched_id)
        scheds = await db.get_user_schedules(user.id)
        text = messages.schedule_info_message(scheds)
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboards.schedule_list_keyboard(scheds),
        )
        return SCHED_SELECT_PRODUCTS

    if data == "sched_new":
        context.user_data["sched_selected"] = set()
        await query.edit_message_text(
            "*New Schedule - Select Products:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboards.product_selection_keyboard(),
        )
        return SCHED_SELECT_PRODUCTS

    # Product selection for schedule
    if data.startswith("sel_prod:"):
        action = data.split(":", 1)[1]
        selected: set[str] = context.user_data.get("sched_selected", set())

        if action == "cancel":
            await query.edit_message_text("Schedule creation cancelled.")
            return ConversationHandler.END

        if action == "all":
            if len(selected) == len(PRODUCT_CATALOG):
                selected.clear()
            else:
                selected = set(PRODUCT_CATALOG.keys())
            context.user_data["sched_selected"] = selected
            await query.edit_message_reply_markup(
                reply_markup=keyboards.product_selection_keyboard(selected)
            )
            return SCHED_SELECT_PRODUCTS

        if action == "confirm":
            if not selected:
                await query.answer("Select at least one product!", show_alert=True)
                return SCHED_SELECT_PRODUCTS

            context.user_data["sched_products"] = {pid: 1 for pid in selected}
            await query.edit_message_text(
                "*Select delivery day:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboards.schedule_day_keyboard(),
            )
            return SCHED_DAY

        if action in PRODUCT_CATALOG:
            if action in selected:
                selected.discard(action)
            else:
                selected.add(action)
            context.user_data["sched_selected"] = selected
            await query.edit_message_reply_markup(
                reply_markup=keyboards.product_selection_keyboard(selected)
            )
        return SCHED_SELECT_PRODUCTS

    return SCHED_SELECT_PRODUCTS


async def schedule_day_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "sched_day:cancel":
        await query.edit_message_text("Schedule creation cancelled.")
        return ConversationHandler.END

    if data.startswith("sched_day:"):
        day = int(data.split(":")[1])
        context.user_data["sched_day"] = day
        await query.edit_message_text(
            f"*Schedule for {DAYS_OF_WEEK[day]}*\nSelect time:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboards.schedule_hour_keyboard(),
        )
        return SCHED_HOUR

    return SCHED_DAY


async def schedule_hour_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "sched_hour:cancel":
        await query.edit_message_text("Schedule creation cancelled.")
        return ConversationHandler.END

    if data.startswith("sched_hour:"):
        hour = int(data.split(":")[1])
        day = context.user_data.get("sched_day", 0)
        products = context.user_data.get("sched_products", {})

        db = _get_db(context)
        user = update.effective_user
        assert user is not None

        schedule = await db.create_schedule(
            user_id=user.id,
            day_of_week=day,
            hour=hour,
            minute=0,
            products=products,
        )

        product_names = []
        for pid in products:
            p = PRODUCT_CATALOG.get(pid)
            if p:
                product_names.append(p.short_name)

        await query.edit_message_text(
            f"*Schedule Created!*\n\n"
            f"*Day:* {DAYS_OF_WEEK[day]}\n"
            f"*Time:* {hour:02d}:00\n"
            f"*Products:* {', '.join(product_names)}\n\n"
            f"You'll receive a reminder every {DAYS_OF_WEEK[day]} at {hour:02d}:00.\n"
            f"Manage your schedules with /schedule",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    return SCHED_HOUR


async def schedule_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if update.message:
        await update.message.reply_text("Schedule setup cancelled.")
    return ConversationHandler.END


# ── Reminder Callbacks (from scheduler) ──


async def reminder_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if not data.startswith("reminder:"):
        return

    parts = data.split(":")
    if len(parts) < 3:
        return

    action = parts[1]
    schedule_id = int(parts[2])

    db = _get_db(context)
    user = update.effective_user
    assert user is not None

    if action == "skip":
        await db.create_order(
            user_id=user.id,
            products={},
            status="skipped",
        )
        await query.edit_message_text("Skipped this week's order.")
        return

    if action == "order":
        scheds = await db.get_user_schedules(user.id)
        target = None
        for s in scheds:
            if s.id == schedule_id:
                target = s
                break

        if not target:
            await query.edit_message_text("Schedule not found.")
            return

        prices_list = await db.get_all_product_prices()
        prices = {pp.product_id: pp.price for pp in prices_list}
        total = sum(
            prices.get(pid, 0.0) * qty for pid, qty in target.products.items()
        )

        order = await db.create_order(
            user_id=user.id,
            products=target.products,
            status="pending",
            total_estimate=total,
        )

        await query.edit_message_text("Preparing your cart on shop.amul.com...")

        cart_mgr = _get_cart_manager(context)
        try:
            checkout_url, errors = await cart_mgr.add_to_cart_and_get_checkout_url(
                target.products
            )
            await db.update_order_status(
                order.id, "cart_ready", checkout_url, total
            )
            text = messages.cart_ready_message(checkout_url, errors)
        except Exception as exc:
            logger.error("Reminder cart flow failed: %s", exc)
            links = await cart_mgr.get_direct_cart_links(target.products)
            await db.update_order_status(order.id, "failed")
            text = messages.cart_fallback_message(links)

        await context.bot.send_message(
            chat_id=user.id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False,
        )
        return

    if action == "change":
        await query.edit_message_text(
            "To change quantities, use /order to create a custom order."
        )


# ── Track Availability ──


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

    # Refresh dashboard after any toggle/clear/refresh
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


# ── Settings ──


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
        await query.edit_message_text(
            "Send me your 6-digit delivery pincode:"
        )
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
        await update.message.reply_text(
            "Please enter a valid 6-digit pincode:"
        )
        return PINCODE_INPUT

    db = _get_db(context)
    user = update.effective_user
    assert user is not None
    await db.update_user_pincode(user.id, text)
    await update.message.reply_text(
        f"Pincode updated to *{text}*. Use /settings to see all settings.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def settings_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    return ConversationHandler.END


# ── Handler Registration ──


def get_all_handlers() -> list:
    """Return all handlers to register with the Application."""
    order_conv = ConversationHandler(
        entry_points=[CommandHandler("order", order_start)],
        states={
            SELECT_PRODUCTS: [
                CallbackQueryHandler(order_select_product, pattern=r"^sel_prod:"),
            ],
            SET_QUANTITIES: [
                CallbackQueryHandler(order_set_quantity, pattern=r"^qty:"),
            ],
            CONFIRM_ORDER: [
                CallbackQueryHandler(order_confirm, pattern=r"^order_confirm:"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", order_cancel),
            CallbackQueryHandler(order_cancel, pattern=r"^noop$"),
        ],
    )

    schedule_conv = ConversationHandler(
        entry_points=[CommandHandler("schedule", schedule_start)],
        states={
            SCHED_SELECT_PRODUCTS: [
                CallbackQueryHandler(
                    schedule_callback,
                    pattern=r"^(sched_toggle:|sched_del:|sched_new|sel_prod:)",
                ),
            ],
            SCHED_DAY: [
                CallbackQueryHandler(schedule_day_callback, pattern=r"^sched_day:"),
            ],
            SCHED_HOUR: [
                CallbackQueryHandler(schedule_hour_callback, pattern=r"^sched_hour:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", schedule_cancel)],
    )

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
        CommandHandler("myorders", myorders_command),
        order_conv,
        schedule_conv,
        settings_conv,
        CallbackQueryHandler(track_callback, pattern=r"^track_"),
        CallbackQueryHandler(reminder_callback, pattern=r"^reminder:"),
    ]
