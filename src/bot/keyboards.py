from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.config import DAYS_OF_WEEK, HOUR_SLOTS, PRODUCT_CATALOG
from src.db.models import Schedule


def product_selection_keyboard(
    selected: set[str] | None = None,
    stock_status: dict[str, bool] | None = None,
) -> InlineKeyboardMarkup:
    """Grid of product toggles with a confirm/cancel row.
    Out-of-stock items are shown but marked and not selectable.
    """
    selected = selected or set()
    stock = stock_status or {}
    rows: list[list[InlineKeyboardButton]] = []

    for pid, product in PRODUCT_CATALOG.items():
        in_stock = stock.get(pid, True)  # assume in-stock if unknown
        if not in_stock:
            rows.append(
                [
                    InlineKeyboardButton(
                        f"[X] {product.short_name} (Out of Stock)",
                        callback_data=f"sel_prod:oos:{pid}",
                    )
                ]
            )
        else:
            check = "  [x]" if pid in selected else ""
            rows.append(
                [
                    InlineKeyboardButton(
                        f"{product.short_name}{check}",
                        callback_data=f"sel_prod:{pid}",
                    )
                ]
            )

    action_row = [
        InlineKeyboardButton("Select All (In Stock)", callback_data="sel_prod:all"),
        InlineKeyboardButton("Confirm", callback_data="sel_prod:confirm"),
    ]
    rows.append(action_row)
    rows.append(
        [InlineKeyboardButton("Cancel", callback_data="sel_prod:cancel")]
    )
    return InlineKeyboardMarkup(rows)


def quantity_keyboard(product_id: str, current_qty: int = 1) -> InlineKeyboardMarkup:
    """Quantity stepper for a single product."""
    rows = [
        [
            InlineKeyboardButton("-", callback_data=f"qty:{product_id}:dec"),
            InlineKeyboardButton(str(current_qty), callback_data="noop"),
            InlineKeyboardButton("+", callback_data=f"qty:{product_id}:inc"),
        ],
        [
            InlineKeyboardButton("Done", callback_data=f"qty:{product_id}:done"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def order_confirm_keyboard(order_id: int | None = None) -> InlineKeyboardMarkup:
    """Final confirmation before placing order."""
    suffix = f":{order_id}" if order_id else ""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Place Order", callback_data=f"order_confirm:yes{suffix}"
                ),
                InlineKeyboardButton(
                    "Cancel", callback_data=f"order_confirm:no{suffix}"
                ),
            ]
        ]
    )


def schedule_day_keyboard() -> InlineKeyboardMarkup:
    """Select day of week for schedule."""
    rows = []
    for i, day in enumerate(DAYS_OF_WEEK):
        rows.append(
            [InlineKeyboardButton(day, callback_data=f"sched_day:{i}")]
        )
    rows.append(
        [InlineKeyboardButton("Cancel", callback_data="sched_day:cancel")]
    )
    return InlineKeyboardMarkup(rows)


def schedule_hour_keyboard() -> InlineKeyboardMarkup:
    """Select hour for schedule."""
    rows = []
    chunk: list[InlineKeyboardButton] = []
    for slot in HOUR_SLOTS:
        hour = int(slot.split(":")[0])
        chunk.append(
            InlineKeyboardButton(slot, callback_data=f"sched_hour:{hour}")
        )
        if len(chunk) == 4:
            rows.append(chunk)
            chunk = []
    if chunk:
        rows.append(chunk)
    rows.append(
        [InlineKeyboardButton("Cancel", callback_data="sched_hour:cancel")]
    )
    return InlineKeyboardMarkup(rows)


def schedule_list_keyboard(schedules: list[Schedule]) -> InlineKeyboardMarkup:
    """List active schedules with delete buttons."""
    rows = []
    for s in schedules:
        day = DAYS_OF_WEEK[s.day_of_week]
        status = "ON" if s.active else "OFF"
        label = f"{day} {s.hour:02d}:{s.minute:02d} [{status}]"
        rows.append(
            [
                InlineKeyboardButton(label, callback_data=f"sched_toggle:{s.id}"),
                InlineKeyboardButton("Delete", callback_data=f"sched_del:{s.id}"),
            ]
        )
    rows.append(
        [InlineKeyboardButton("+ New Schedule", callback_data="sched_new")]
    )
    return InlineKeyboardMarkup(rows)


def reminder_action_keyboard(schedule_id: int) -> InlineKeyboardMarkup:
    """Buttons shown on a scheduled reminder."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Order Now", callback_data=f"reminder:order:{schedule_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Skip This Week",
                    callback_data=f"reminder:skip:{schedule_id}",
                ),
                InlineKeyboardButton(
                    "Change Qty",
                    callback_data=f"reminder:change:{schedule_id}",
                ),
            ],
        ]
    )


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

    bottom_row = [
        InlineKeyboardButton("Refresh", callback_data="track_refresh"),
    ]
    if watchlist:
        bottom_row.append(
            InlineKeyboardButton("Clear All", callback_data="track_clear"),
        )
    rows.append(bottom_row)
    return InlineKeyboardMarkup(rows)


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
