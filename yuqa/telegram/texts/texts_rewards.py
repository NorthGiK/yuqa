"""Free reward text renderers."""

from yuqa.players.domain.entities import Player
from yuqa.telegram.texts.texts_shared import _cooldown_line


def free_rewards_text(
    player: Player, status: dict[str, object], notice: str | None = None
) -> str:
    """Build the free rewards screen."""

    card_ready_at = status["card_ready_at"]
    resource_ready_at = status["resource_ready_at"]
    lines = [
        "🎁 <b>Бесплатные награды</b>",
        "<i>Каждую категорию можно забирать раз в 2 часа.</i>",
        "",
        f"🎴 <b>Карта:</b> {_cooldown_line(card_ready_at)}",
        f"💰 <b>Ресурсы:</b> {_cooldown_line(resource_ready_at)}",
        "",
        f"📚 <b>Коллекция:</b> <code>{player.collection_count}</code>",
        f"🪙 <b>Монеты:</b> <code>{player.wallet.coins}</code>",
        f"💎 <b>Кристаллы:</b> <code>{player.wallet.crystals}</code>",
        f"🔮 <b>Орбы:</b> <code>{player.wallet.orbs}</code>",
    ]
    if notice:
        lines.extend(["", notice])
    return "\n".join(lines)


def free_rewards_admin_text(settings: dict[str, dict[str, int]]) -> str:
    """Render free reward configuration for admins."""

    card_weights = settings["card_weights"]
    resource_weights = settings["resource_weights"]
    resource_values = settings["resource_values"]
    return "\n".join(
        [
            "🎁 <b>Бесплатные награды</b>",
            "<i>Отдельные кулдауны: карта и ресурсы, по 2 часа.</i>",
            "",
            "🎴 <b>Шансы редкости карты:</b>",
            *[
                f"• <code>{name}</code> = <code>{value}</code>"
                for name, value in card_weights.items()
            ],
            "",
            "💰 <b>Шансы типа ресурса:</b>",
            *[
                f"• <code>{name}</code> = <code>{value}</code>"
                for name, value in resource_weights.items()
            ],
            "",
            "📦 <b>Значения ресурсов:</b>",
            *[
                f"• <code>{name}</code> = <code>{value}</code>"
                for name, value in resource_values.items()
            ],
        ]
    )


def free_rewards_edit_guide(mode: str) -> str:
    """Explain how an admin should edit one free reward config block."""

    examples = {
        "card_weights": "common=50 rare=25 epic=15 mythic=5 legendary=4 godly=1",
        "resource_weights": "coins=50 crystals=30 orbs=20",
        "resource_values": "coins=1000 crystals=25 orbs=1",
    }
    titles = {
        "card_weights": "🎴 <b>Шансы редкости карты</b>",
        "resource_weights": "💰 <b>Шансы типа ресурса</b>",
        "resource_values": "📦 <b>Значения ресурсов</b>",
    }
    return (
        f"{titles[mode]}\n"
        "<i>Введи все пары в одной строке через пробел.</i>\n\n"
        f"<b>Пример:</b> <code>{examples[mode]}</code>"
    )


__all__ = [
    "free_rewards_admin_text",
    "free_rewards_edit_guide",
    "free_rewards_text",
]
