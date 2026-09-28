"""aiogram wiring for the demo bot. Pure logic lives in ``text.py``."""

from __future__ import annotations

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from . import text


def main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for label, data in text.main_menu():
        builder.button(text=label, callback_data=data)
    builder.adjust(2)
    return builder.as_markup()


def app_keyboard(web_app_url: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(
        text=text.APP_BUTTON, web_app=WebAppInfo(url=web_app_url)
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


async def set_score(bot: Bot, message: Message, game_message_id: int, args) -> None:
    """Handle `/score [N]`: setGameScore on the chat's game message.

    Without N the score becomes the user's current one plus 1, read with
    getGameHighScores (a bot-only method), so repeated runs always change it.
    """
    try:
        points = text.parse_score(args)
    except ValueError:
        await message.answer(text.SCORE_USAGE)
        return
    where = {
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "message_id": game_message_id,
    }
    if points is None:
        table = await bot.get_game_high_scores(**where)
        mine = [row.score for row in table if row.user.id == message.from_user.id]
        points = (mine[0] if mine else 0) + 1
    try:
        await bot.set_game_score(score=points, force=True, **where)
    except TelegramBadRequest:
        await message.answer(text.SCORE_UNCHANGED)


def games_router(game_short_name: str, game_url: str, web_app_url: str) -> Router:
    """Handlers for the game (/game, Play, /score) and the Mini App (/app)."""
    router = Router()
    games: dict[int, int] = {}  # chat id -> id of the last game message

    @router.message(Command("game"))
    async def on_game(message: Message) -> None:
        sent = await message.answer_game(game_short_name)
        games[message.chat.id] = sent.message_id

    @router.message(Command("score"))
    async def on_score(message: Message, command: CommandObject) -> None:
        game_message_id = games.get(message.chat.id)
        if game_message_id is None:
            await message.answer(text.NO_GAME)
            return
        await set_score(message.bot, message, game_message_id, command.args)

    @router.callback_query(F.game_short_name == game_short_name)
    async def on_play(callback: CallbackQuery) -> None:
        await callback.answer(url=text.game_link(game_url, callback.from_user.id))

    @router.message(Command("app"))
    async def on_app(message: Message) -> None:
        await message.answer(text.APP_PROMPT, reply_markup=app_keyboard(web_app_url))

    return router


def menu_router() -> Router:
    """/start, /help, the inline menu, echo and the unknown-command fallback."""
    router = Router()

    @router.message(CommandStart())
    async def on_start(message: Message) -> None:
        await message.answer(text.WELCOME, reply_markup=main_keyboard())

    @router.message(Command("help"))
    async def on_help(message: Message) -> None:
        await message.answer(text.HELP)

    @router.callback_query(F.data == "settings")
    async def on_settings(callback: CallbackQuery) -> None:
        await callback.message.edit_text(text.SETTINGS)
        await callback.answer()

    @router.callback_query(F.data == "help")
    async def on_help_button(callback: CallbackQuery) -> None:
        await callback.message.edit_text(text.HELP)
        await callback.answer()

    @router.message(F.text & ~F.text.startswith("/"))
    async def on_text(message: Message) -> None:
        await message.answer(text.reply_for(message.text))

    @router.message(F.text.startswith("/"))
    async def on_unknown(message: Message) -> None:
        await message.answer(text.UNKNOWN)

    return router


def build_dispatcher(
    game_short_name: str = text.GAME_SHORT_NAME,
    game_url: str = text.GAME_URL,
    web_app_url: str = text.WEB_APP_URL,
) -> Dispatcher:
    """Build a Dispatcher with all handlers registered (no Bot/token needed).

    The games router comes first so its commands win over the menu router's
    unknown-command fallback.
    """
    dp = Dispatcher()
    dp.include_router(games_router(game_short_name, game_url, web_app_url))
    dp.include_router(menu_router())
    return dp
