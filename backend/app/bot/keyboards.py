"""Inline keyboards for the customer bot."""
from __future__ import annotations

from typing import Iterable, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.locales import translate
from app.bot.utils import format_amount, is_auto, localized_name, status_label


def _rows(buttons: Iterable[InlineKeyboardButton], per_row: int = 1) -> list:
    buttons = list(buttons)
    return [buttons[i : i + per_row] for i in range(0, len(buttons), per_row)]


def main_menu(language: str, support_username: Optional[str] = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=translate(language, "btn.catalog"), callback_data="menu:catalog")],
        [InlineKeyboardButton(text=translate(language, "btn.orders"), callback_data="menu:orders")],
        [
            InlineKeyboardButton(text=translate(language, "btn.support"), callback_data="menu:support"),
            InlineKeyboardButton(text=translate(language, "btn.language"), callback_data="menu:language"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_keyboard(language: str, callback: str = "menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=translate(language, "btn.back"), callback_data=callback),
                InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu"),
            ]
        ]
    )


def categories_keyboard(categories, language: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{category.icon or '•'} {localized_name(category, language)}".strip()[:60],
                callback_data=f"cat:{category.id}",
            )
        ]
        for category in categories
    ]
    rows.append(
        [InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_keyboard(products, category_id: int, language: str) -> InlineKeyboardMarkup:
    rows = []
    for product in products:
        stock = int(getattr(product, "stock_available", 0) or 0)
        suffix = f" • {stock}" if is_auto(product) else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{localized_name(product, language)} • {format_amount(product.price, product.currency)}{suffix}"[:60],
                    callback_data=f"prod:{product.id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=translate(language, "btn.back"), callback_data="menu:catalog"
            ),
            InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_keyboard(product, language: str) -> InlineKeyboardMarkup:
    rows = []
    available = int(getattr(product, "stock_available", 0) or 0)
    auto = is_auto(product)
    if not auto or available > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text=translate(language, "qty.buy"),
                    callback_data=f"buy:{product.id}",
                )
            ]
        )
    back = f"cat:{product.category_id}" if product.category_id else "menu:catalog"
    rows.append(
        [
            InlineKeyboardButton(text=translate(language, "btn.back"), callback_data=back),
            InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quantity_keyboard(product, quantity: int, language: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="−", callback_data=f"qty:{product.id}:{max(quantity - 1, product.min_quantity)}"),
            InlineKeyboardButton(text=f"{quantity}", callback_data="noop"),
            InlineKeyboardButton(text="+", callback_data=f"qty:{product.id}:{min(quantity + 1, product.max_quantity)}"),
        ],
        [
            InlineKeyboardButton(
                text=translate(language, "qty.buy"),
                callback_data=f"checkout:{product.id}:{quantity}",
            )
        ],
        [
            InlineKeyboardButton(text=translate(language, "btn.back"), callback_data=f"prod:{product.id}"),
            InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def checkout_keyboard(
    product_id: int, quantity: int, language: str, voucher_code: Optional[str] = None
) -> InlineKeyboardMarkup:
    pay_data = f"pay:{product_id}:{quantity}"
    if voucher_code:
        pay_data += f":{voucher_code}"
    rows = [
        [
            InlineKeyboardButton(
                text=translate(language, "btn.pay"), callback_data=pay_data[:64]
            )
        ],
        [
            InlineKeyboardButton(
                text=translate(language, "btn.voucher"),
                callback_data=f"vouch:{product_id}:{quantity}",
            )
        ],
        [
            InlineKeyboardButton(
                text=translate(language, "btn.back"),
                callback_data=f"buy:{product_id}",
            ),
            InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def invoice_keyboard(order, language: str) -> InlineKeyboardMarkup:
    invoice = order.active_invoice
    rows = []
    if invoice is not None and invoice.payment_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text=translate(language, "invoice.open"), url=invoice.payment_url
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=translate(language, "invoice.check"),
                callback_data=f"check:{order.id}",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=translate(language, "invoice.cancel"),
                callback_data=f"cancel:{order.id}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def orders_keyboard(orders, language: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=translate(
                    language,
                    "orders.button",
                    code=order.order_code,
                    status=status_label(order.status, language),
                )[:60],
                callback_data=f"order:{order.id}",
            )
        ]
        for order in orders
    ]
    rows.append(
        [InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_keyboard(order, language: str) -> InlineKeyboardMarkup:
    rows = []
    if order.delivery is not None and order.delivery.delivered_content:
        rows.append(
            [
                InlineKeyboardButton(
                    text=translate(language, "order.view_content"),
                    callback_data=f"content:{order.id}",
                )
            ]
        )
    if order.status == "PENDING_PAYMENT" or order.status == "PAID":
        rows.append(
            [
                InlineKeyboardButton(
                    text=translate(language, "invoice.check"),
                    callback_data=f"check:{order.id}",
                )
            ]
        )
    if order.status == "PENDING_PAYMENT":
        rows.append(
            [
                InlineKeyboardButton(
                    text=translate(language, "invoice.cancel"),
                    callback_data=f"cancel:{order.id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text=translate(language, "btn.back"), callback_data="menu:orders"),
            InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def support_keyboard(language: str, support_username: Optional[str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=translate(language, "support.new"), callback_data="support:new")],
        [InlineKeyboardButton(text=translate(language, "support.my"), callback_data="support:list")],
    ]
    if support_username:
        username = support_username.lstrip("@")
        rows.append(
            [
                InlineKeyboardButton(
                    text=translate(language, "support.contact"),
                    url=f"https://t.me/{username}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def language_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇮🇩 Bahasa Indonesia", callback_data="lang:id")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
            [InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu")],
        ]
    )


def ticket_list_keyboard(tickets, language: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{ticket.ticket_code} • {status_label(ticket.status, language)}",
                callback_data=f"tkt:{ticket.id}",
            )
        ]
        for ticket in tickets
    ]
    rows.append(
        [
            InlineKeyboardButton(text=translate(language, "btn.back"), callback_data="menu:support"),
            InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ticket_thread_keyboard(ticket, language: str) -> InlineKeyboardMarkup:
    rows = []
    if ticket.status != "CLOSED":
        rows.append(
            [
                InlineKeyboardButton(
                    text=translate(language, "support.reply"),
                    callback_data=f"tktreply:{ticket.id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text=translate(language, "btn.back"), callback_data="support:list"),
            InlineKeyboardButton(text=translate(language, "btn.menu"), callback_data="menu"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
