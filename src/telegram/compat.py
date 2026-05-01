"""Compatibility layer for aiogram and test-friendly stand-ins."""

from dataclasses import dataclass

try:
    from aiogram import BaseMiddleware as _BaseMiddleware
    from aiogram import Bot as _Bot
    from aiogram import Dispatcher as _Dispatcher
    from aiogram import Router as _Router
    from aiogram.client.default import DefaultBotProperties as _DefaultBotProperties
    from aiogram.enums import ParseMode as _ParseMode
    from aiogram.exceptions import TelegramBadRequest as _TelegramBadRequest
    from aiogram.filters import Command as _Command
    from aiogram.filters import CommandObject as _CommandObject
    from aiogram.filters import CommandStart as _CommandStart
    from aiogram.filters.callback_data import CallbackData as _CallbackData
    from aiogram.fsm.state import State as _State
    from aiogram.fsm.state import StatesGroup as _StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage as _MemoryStorage
    from aiogram.types import (
        CallbackQuery as _AiogramCallbackQuery,
        FSInputFile as _FSInputFile,
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        KeyboardButton,
        ReplyKeyboardMarkup,
        Message as _AiogramMessage,
        User as _AiogramUser,
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder as _InlineKeyboardBuilder
    from aiogram.utils.keyboard import ReplyKeyboardBuilder as _ReplyKeyboardBuilder
except Exception:  # pragma: no cover - used when aiogram is unavailable
    _BaseMiddleware = None
    _Bot = None
    _Dispatcher = None
    _Router = None
    _DefaultBotProperties = None
    _ParseMode = None
    _TelegramBadRequest = None
    _Command = None
    _CommandObject = None
    _CommandStart = None
    _CallbackData = None
    _State = None
    _StatesGroup = None
    _MemoryStorage = None
    _InlineKeyboardBuilder = None
    _ReplyKeyboardBuilder = None
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None
    KeyboardButton = None
    ReplyKeyboardMarkup = None
    _AiogramMessage = None
    _AiogramCallbackQuery = None
    _AiogramUser = None
    _FSInputFile = None


class TelegramBadRequest(Exception):
    """Fallback Telegram API error."""


class BaseMiddleware:
    """No-op middleware base class."""

    async def __call__(self, handler, event, data):
        return await handler(event, data)


if _Router is None:

    class Router:
        """Tiny router stand-in for tests."""

        def __init__(self, name: str | None = None) -> None:
            self.name = name or "router"
            self.handlers = []

        def include_router(self, router):
            self.handlers.append(router)
            return router

        def message(self, *filters):
            def decorator(func):
                self.handlers.append(("message", filters, func))
                return func

            return decorator

        def callback_query(self, *filters):
            def decorator(func):
                self.handlers.append(("callback_query", filters, func))
                return func

            return decorator

    class Dispatcher(Router):
        """Router with a polling entrypoint."""

        def __init__(self, storage=None) -> None:
            super().__init__("dispatcher")
            self.storage = storage

        async def start_polling(self, bot):
            return None

    class Bot:
        """Lightweight bot placeholder."""

        def __init__(self, token: str, default=None) -> None:
            self.token = token
            self.default = default

    class DefaultBotProperties:
        """Placeholder for aiogram defaults."""

        def __init__(self, parse_mode=None) -> None:
            self.parse_mode = parse_mode

    class ParseMode:
        """Subset of aiogram parse modes."""

        HTML = "HTML"

    class Command:
        def __init__(self, *values):
            self.values = values

    class CommandStart(Command):
        pass

    @dataclass(slots=True)
    class CommandObject:
        args: str | None = None

    class State:
        pass

    class StatesGroup:
        pass

    class MemoryStorage:
        pass

    @dataclass(slots=True)
    class InlineKeyboardMarkup:
        inline_keyboard: list[list[tuple[str, str]]]

    @dataclass(slots=True)
    class KeyboardButton:
        """Tiny reply keyboard button stand-in."""

        text: str

    @dataclass(slots=True)
    class ReplyKeyboardMarkup:
        """Tiny reply keyboard stand-in."""

        keyboard: list[list[KeyboardButton]]
        resize_keyboard: bool = True
        one_time_keyboard: bool = False
        input_field_placeholder: str | None = None
        selective: bool = False

    class InlineKeyboardBuilder:
        """Tiny keyboard builder used in tests."""

        def __init__(self) -> None:
            self._buttons = []
            self._sizes = []

        def button(self, text, callback_data):
            if hasattr(callback_data, "pack"):
                callback_data = callback_data.pack()
            self._buttons.append((text, callback_data))

        def adjust(self, *sizes):
            self._sizes = list(sizes)

        def as_markup(self):
            if not self._buttons:
                return InlineKeyboardMarkup([])
            sizes = self._sizes or [len(self._buttons)]
            rows = []
            index = 0
            for size in sizes:
                rows.append(self._buttons[index : index + size])
                index += size
            if index < len(self._buttons):
                rows.append(self._buttons[index:])
            return InlineKeyboardMarkup(rows)

    class ReplyKeyboardBuilder:
        """Tiny reply-keyboard builder used in tests."""

        def __init__(self) -> None:
            self._buttons = []
            self._sizes = []

        def button(self, text):
            self._buttons.append(KeyboardButton(text=text))

        def adjust(self, *sizes: int):
            self._sizes = list(sizes)

        def as_markup(
            self,
            *,
            resize_keyboard: bool = True,
            one_time_keyboard: bool = False,
            input_field_placeholder: str | None = None,
            selective: bool = False,
        ):
            if not self._buttons:
                return ReplyKeyboardMarkup(
                    [],
                    resize_keyboard=resize_keyboard,
                    one_time_keyboard=one_time_keyboard,
                    input_field_placeholder=input_field_placeholder,
                    selective=selective,
                )
            sizes = self._sizes or [len(self._buttons)]
            rows = []
            index = 0
            for size in sizes:
                rows.append(self._buttons[index : index + size])
                index += size
            if index < len(self._buttons):
                rows.append(self._buttons[index:])
            return ReplyKeyboardMarkup(
                rows,
                resize_keyboard=resize_keyboard,
                one_time_keyboard=one_time_keyboard,
                input_field_placeholder=input_field_placeholder,
                selective=selective,
            )

    class CallbackData:
        """Compact callback data wrapper."""

        prefix = ""
        sep = ":"
        _fields: tuple[str, ...] = ()

        def __init_subclass__(cls, prefix: str = "", sep: str = ":", **kwargs):
            super().__init_subclass__(**kwargs)
            cls.prefix = prefix
            cls.sep = sep
            cls._fields = tuple(cls.__annotations__)

            def __init__(self, **data):
                for name in cls._fields:
                    setattr(self, name, data.get(name, getattr(cls, name, None)))

            cls.__init__ = __init__

        def pack(self):
            return (
                self.prefix
                + self.sep
                + self.sep.join(str(getattr(self, name)) for name in self._fields)
            )

        @classmethod
        def filter(cls, *args, **kwargs):
            return cls


else:
    BaseMiddleware = _BaseMiddleware
    Bot = _Bot
    Dispatcher = _Dispatcher
    Router = _Router
    DefaultBotProperties = _DefaultBotProperties
    ParseMode = _ParseMode
    TelegramBadRequest = _TelegramBadRequest
    Command = _Command
    CommandObject = _CommandObject
    CommandStart = _CommandStart
    CallbackData = _CallbackData
    State = _State
    StatesGroup = _StatesGroup
    MemoryStorage = _MemoryStorage
    InlineKeyboardBuilder = _InlineKeyboardBuilder
    ReplyKeyboardBuilder = _ReplyKeyboardBuilder
    InlineKeyboardMarkup = InlineKeyboardMarkup
    FSInputFile = _FSInputFile

    def _button_getitem(self, index: int):
        return (self.text, self.callback_data)[index]

    InlineKeyboardButton.__getitem__ = _button_getitem  # type: ignore[attr-defined]


if _FSInputFile is None:

    @dataclass(slots=True)
    class FSInputFile:
        """Tiny local-file wrapper compatible with aiogram's constructor."""

        path: object


@dataclass(slots=True)
class User:
    """Simple Telegram user stand-in."""

    id: int
    username: str | None = None


class Message:
    """Simple Telegram message stand-in."""

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
    """Simple Telegram callback query stand-in."""

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
    "BaseMiddleware",
    "Bot",
    "CallbackData",
    "CallbackQuery",
    "Command",
    "CommandObject",
    "CommandStart",
    "DefaultBotProperties",
    "Dispatcher",
    "FSMContext",
    "FSInputFile",
    "InlineKeyboardBuilder",
    "InlineKeyboardMarkup",
    "KeyboardButton",
    "MemoryStorage",
    "Message",
    "ParseMode",
    "ReplyKeyboardBuilder",
    "ReplyKeyboardMarkup",
    "Router",
    "State",
    "StatesGroup",
    "TelegramBadRequest",
    "User",
]
