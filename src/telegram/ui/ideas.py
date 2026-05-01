"""Idea browsing and moderation keyboards."""

from src.ideas.domain.entities import Idea
from src.shared.enums import IdeaStatus
from src.telegram.callbacks import AdminCallback, IdeaCallback
from src.telegram.compat import InlineKeyboardMarkup
from src.telegram.ui.helpers import _markup


def ideas_markup(
    ideas: list[Idea],
    page: int,
    *,
    has_prev: bool,
    has_next: bool,
    collection: bool = False,
) -> InlineKeyboardMarkup:
    """Return the public ideas or collection keyboard."""

    scope = "collection" if collection else "published"
    buttons = [
        (
            f"💡 {idea.title[:24]}{'…' if len(idea.title) > 24 else ''} · 👍 {idea.upvotes}",
            IdeaCallback(action="open", idea_id=idea.id, page=page, scope=scope),
        )
        for idea in ideas
    ]
    nav = []
    if has_prev:
        nav.append(("⬅️", IdeaCallback(action="page", page=page - 1, scope=scope)))
    if has_next:
        nav.append(("➡️", IdeaCallback(action="page", page=page + 1, scope=scope)))
    buttons.extend(nav)
    if not collection:
        buttons.append(
            ("➕ Предложить идею", IdeaCallback(action="propose", page=page))
        )
    sizes = [1] * len(ideas)
    if nav:
        sizes.append(len(nav))
    if not collection:
        sizes.append(1)
    return _markup(buttons, tuple(sizes))


def idea_detail_markup(
    idea_id: int,
    page: int,
    *,
    scope: str,
    can_vote: bool,
) -> InlineKeyboardMarkup:
    """Return the public idea detail keyboard."""

    buttons = []
    if can_vote:
        buttons.extend(
            [
                (
                    "👍 За",
                    IdeaCallback(
                        action="vote_up",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
                (
                    "👎 Против",
                    IdeaCallback(
                        action="vote_down",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
            ]
        )
    return _markup(buttons, (2,) if can_vote else ())


def admin_ideas_markup(
    ideas: list[Idea],
    page: int,
    *,
    scope: str,
    has_prev: bool,
    has_next: bool,
) -> InlineKeyboardMarkup:
    """Return the admin ideas browser keyboard."""

    buttons = [
        (
            f"💡 {idea.title[:22]}{'…' if len(idea.title) > 22 else ''} · 👍 {idea.upvotes}",
            IdeaCallback(action="open", idea_id=idea.id, page=page, scope=scope),
        )
        for idea in ideas
    ]
    buttons.extend(
        [
            ("🆕 Модерация", IdeaCallback(action="admin_list", scope="admin_pending")),
            ("📣 Паблик", IdeaCallback(action="admin_list", scope="admin_public")),
            (
                "📚 Коллекция",
                IdeaCallback(action="admin_list", scope="admin_collection"),
            ),
            (
                "🗑 Архив",
                IdeaCallback(action="admin_list", scope="admin_rejected"),
            ),
        ]
    )
    nav = []
    if has_prev:
        nav.append(("⬅️", IdeaCallback(action="admin_list", page=page - 1, scope=scope)))
    if has_next:
        nav.append(("➡️", IdeaCallback(action="admin_list", page=page + 1, scope=scope)))
    buttons.extend(nav)
    buttons.append(("🏠 Панель", AdminCallback(action="section", value="dashboard")))
    sizes = [1] * len(ideas)
    sizes.extend((2, 2))
    if nav:
        sizes.append(len(nav))
    sizes.append(1)
    return _markup(buttons, tuple(sizes))


def admin_idea_detail_markup(
    idea_id: int,
    page: int,
    *,
    scope: str,
    status: IdeaStatus,
) -> InlineKeyboardMarkup:
    """Return the admin idea detail keyboard."""

    buttons = []
    if status == IdeaStatus.PENDING:
        buttons.extend(
            [
                (
                    "✅ На страницу идей",
                    IdeaCallback(
                        action="admin_publish",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
                (
                    "🗑 Отклонить",
                    IdeaCallback(
                        action="admin_reject",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
            ]
        )
    elif status == IdeaStatus.PUBLISHED:
        buttons.extend(
            [
                (
                    "📚 В коллекцию",
                    IdeaCallback(
                        action="admin_collect",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
                (
                    "🗑 Отклонить",
                    IdeaCallback(
                        action="admin_reject",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
            ]
        )
    return _markup(buttons, (2,) if len(buttons) > 1 else ())


__all__ = [
    "admin_idea_detail_markup",
    "admin_ideas_markup",
    "idea_detail_markup",
    "ideas_markup",
]
