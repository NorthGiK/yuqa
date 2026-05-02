"""Test-only Telegram stand-ins for handler and helper tests."""

from dataclasses import dataclass

from aiogram.exceptions import TelegramBadRequest


@dataclass(slots=True)
class User:
    """Tiny Telegram user stand-in."""

    id: int
    username: str | None = None


class Message:
    """Tiny Telegram message stand-in."""

    __slots__ = (
        "from_user",
        "text",
        "reply_markup",
        "answered_text",
        "answered_photo",
        "answered_document",
        "answered_video",
        "caption",
        "photo",
        "video",
        "document",
        "bot",
    )

    def __init__(
        self,
        from_user: User | None = None,
        text: str | None = None,
        reply_markup: object | None = None,
        photo: object | None = None,
        video: object | None = None,
        document: object | None = None,
        bot: object | None = None,
        **_: object,
    ) -> None:
        self.from_user = from_user
        self.text = text
        self.reply_markup = reply_markup
        self.photo = photo
        self.video = video
        self.document = document
        self.bot = bot
        self.answered_text = None
        self.answered_photo = None
        self.answered_document = None
        self.answered_video = None
        self.caption = None

    async def answer(self, text, reply_markup=None, **_: object):
        self.text = text
        self.answered_text = text
        self.reply_markup = reply_markup
        return self

    async def answer_photo(self, photo, caption=None, reply_markup=None, **_: object):
        self.photo = photo
        self.answered_photo = photo
        self.caption = caption
        self.reply_markup = reply_markup
        return self

    async def answer_document(
        self, document, caption=None, reply_markup=None, **_: object
    ):
        self.document = document
        self.answered_document = document
        self.caption = caption
        self.reply_markup = reply_markup
        return self

    async def answer_video(self, video, caption=None, reply_markup=None, **_: object):
        self.video = video
        self.answered_video = video
        self.caption = caption
        self.reply_markup = reply_markup
        return self

    async def edit_text(self, text, reply_markup=None, **_: object):
        self.text = text
        self.answered_text = text
        self.reply_markup = reply_markup
        return self


class CallbackQuery:
    """Tiny Telegram callback query stand-in."""

    __slots__ = ("from_user", "message", "data", "answered_text", "alert")

    def __init__(
        self,
        from_user: User | None = None,
        message: Message | None = None,
        data: str | None = None,
        **_: object,
    ) -> None:
        self.from_user = from_user
        self.message = message
        self.data = data
        self.answered_text = None
        self.alert = False

    async def answer(self, text=None, show_alert=False, **_: object):
        self.answered_text = text
        self.alert = show_alert
        return None


@dataclass(slots=True)
class CommandObject:
    """Tiny command-argument stand-in."""

    args: str | None = None


class FSMContext:
    """Minimal in-memory FSM context."""

    __slots__ = ("state", "data")

    def __init__(self) -> None:
        self.state = None
        self.data = {}

    async def set_state(self, state):
        self.state = state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)
        return self.data

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.state = None
        self.data.clear()


__all__ = [
    "CallbackQuery",
    "CommandObject",
    "FSMContext",
    "Message",
    "TelegramBadRequest",
    "User",
]
