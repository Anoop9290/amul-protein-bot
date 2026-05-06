from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.config import PRODUCT_CATALOG


def track_keyboard(
    watchlist: set[str],
    stock_status: dict[str, bool],
) -> InlineKeyboardMarkup:
    """Availability dashboard with watch/unwatch toggles."""
    rows: list[list[InlineKeyboardButton]] = []

    for pid, product in PRODUCT_CATALOG.items():
        in_stock = stock_status.get(pid)
        if in_stock is True:
            icon = "[OK]"
        elif in_stock is False:
            icon = "[X]"
        else:
            icon = "[?]"

        watching = pid in watchlist
        action_label = "Unwatch" if watching else "Watch"
        action_icon = "(-)" if watching else "(+)"

        rows.append(
            [
                InlineKeyboardButton(
                    f"{icon} {product.short_name}",
                    callback_data=f"track_info:{pid}",
                ),
                InlineKeyboardButton(
                    f"{action_icon} {action_label}",
                    callback_data=f"track_toggle:{pid}",
                ),
            ]
        )

    action_row = [
        InlineKeyboardButton("Refresh", callback_data="track_refresh"),
    ]
    if watchlist:
        action_row.append(
            InlineKeyboardButton("Clear All", callback_data="track_clear"),
        )
    rows.append(action_row)
    rows.append(
        [InlineKeyboardButton("Back to Products", callback_data="track_back_products")]
    )
    return InlineKeyboardMarkup(rows)


def products_keyboard() -> InlineKeyboardMarkup:
    """Button shown below the /products list to jump to tracking."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Track Availability", callback_data="open_track"
                ),
                InlineKeyboardButton(
                    "Refresh Prices", callback_data="refresh_products"
                ),
            ],
        ]
    )


def settings_keyboard(notifications_on: bool) -> InlineKeyboardMarkup:
    notif_label = "Notifications: ON" if notifications_on else "Notifications: OFF"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Set Pincode", callback_data="settings:pincode"
                ),
            ],
            [
                InlineKeyboardButton(
                    notif_label, callback_data="settings:toggle_notif"
                ),
            ],
        ]
    )
