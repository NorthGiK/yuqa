"""Idea text renderers."""

from html import escape

from src.ideas.domain.entities import Idea
from src.players.domain.entities import Player
from src.telegram.texts.shared import _idea_status_label, _player_name


def ideas_text(
    ideas: list[Idea],
    page: int,
    *,
    title: str = "💡 <b>Идеи</b>",
    empty_text: str = "Пока идей нет.",
) -> str:
    """Render one page of idea titles with upvote counts."""

    if not ideas:
        return f"{title}\n<i>{empty_text}</i>"
    lines = [title, f"📄 <b>Страница:</b> <code>{page}</code>", ""]
    for idea in ideas:
        lines.append(f"• <b>{escape(idea.title)}</b> — 👍 <code>{idea.upvotes}</code>")
    return "\n".join(lines)


def idea_text(
    idea: Idea, author: Player | None, *, viewer_vote: int | None = None
) -> str:
    """Render one idea with author, body, and vote counters."""

    lines = [
        f"👤 <b>Автор:</b> {_player_name(author) if author else f'Игрок <code>{idea.player_id}</code>'}",
        "",
        f"💡 <b>{escape(idea.title)}</b>",
        escape(idea.description),
        "",
        f"👍 <b>За:</b> <code>{idea.upvotes}</code>",
        f"👎 <b>Против:</b> <code>{idea.downvotes}</code>",
        f"📌 <b>Статус:</b> <code>{_idea_status_label(idea.status)}</code>",
    ]
    if viewer_vote is not None:
        lines.append(
            f"🗳 <b>Твой голос:</b> <code>{'за' if viewer_vote > 0 else 'против'}</code>"
        )
    return "\n".join(lines)


def idea_wizard_text(step: str, draft: dict) -> str:
    """Render the player idea proposal flow."""

    return (
        "💡 <b>Новая идея механики</b>\n"
        f"<i>Шаг:</i> <code>{step}</code>\n\n"
        f"<b>Название:</b> {escape(str(draft.get('title', '—')))}\n"
        f"<b>Описание:</b> {escape(str(draft.get('description', '—')))}\n\n"
        "<i>После отправки идея попадёт на модерацию к администратору.</i>"
    )


__all__ = ["idea_text", "idea_wizard_text", "ideas_text"]
