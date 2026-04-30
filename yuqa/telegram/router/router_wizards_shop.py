"""Shop wizard flows for admin content management."""

from yuqa.shared.enums import ResourceType
from yuqa.telegram.compat import FSMContext, Message
from yuqa.telegram.router.router_helpers import _parse_int
from yuqa.telegram.states import ShopCreate
from yuqa.telegram.texts.texts import shop_wizard_text
from yuqa.telegram.ui.ui import admin_choice_markup


async def start_shop_create(message: Message, state: FSMContext):
    """Start the shop item wizard."""

    await state.clear()
    await state.set_state(ShopCreate.sell_resource)
    await message.answer(
        shop_wizard_text("что продаём", {}),
        reply_markup=admin_choice_markup(
            "shop_sell", [(item.value, item.value) for item in ResourceType], "shop"
        ),
    )


async def shop_price(message: Message, state: FSMContext):
    """Store the price and ask for quantity."""

    await state.update_data(
        price=_parse_int(message.text or "0", "price", positive=True)
    )
    await state.set_state(ShopCreate.quantity)
    await message.answer("Сколько товара выдаём? 📦")


async def shop_quantity(message: Message, state: FSMContext):
    """Store the quantity and ask whether the item is active."""

    await state.update_data(
        quantity=_parse_int(message.text or "0", "quantity", positive=True)
    )
    await state.set_state(ShopCreate.active)
    await message.answer(
        "Товар активен?",
        reply_markup=admin_choice_markup(
            "shop_active", [("Да", "yes"), ("Нет", "no")], "shop"
        ),
    )


__all__ = [
    "shop_price",
    "shop_quantity",
    "start_shop_create",
]
