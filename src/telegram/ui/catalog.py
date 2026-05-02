"""Shop and banner keyboards."""

from aiogram.types import InlineKeyboardMarkup

from src.telegram.callbacks import BannerCallback, MenuCallback, ShopCallback
from src.telegram.ui.helpers import _markup


def shop_markup(item_ids: list[int]) -> InlineKeyboardMarkup:
    """Return the shop catalog keyboard."""

    buttons = [
        (f"🛒 Купить #{item_id}", ShopCallback(action="buy", item_id=item_id))
        for item_id in item_ids
    ]
    buttons.append(("🎁 Бесплатно", MenuCallback(section="free_rewards")))
    sizes = [2] * (len(item_ids) // 2)
    if len(item_ids) % 2:
        sizes.append(1)
    sizes.append(1)
    return _markup(buttons, tuple(sizes))


def banner_markup(banner_id: int) -> InlineKeyboardMarkup:
    """Return the banner detail keyboard."""

    return _markup(
        [
            (
                "🎲 Крутка x1",
                BannerCallback(action="pull", banner_id=banner_id, count=1),
            ),
            (
                "✨ Крутка x10",
                BannerCallback(action="pull", banner_id=banner_id, count=10),
            ),
        ],
        (2,),
    )


__all__ = ["banner_markup", "shop_markup"]
