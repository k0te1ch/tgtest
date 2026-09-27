"""aiogram wiring for the demo bot. Pure logic lives in ``text.py``."""

from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
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


def build_dispatcher(
    game_short_name: str = text.GAME_SHORT_NAME,
    game_url: str = text.GAME_URL,
    web_app_url: str = text.WEB_APP_URL,
) -> Dispatcher:
    """Build a Dispatcher with all handlers registered (no Bot/token needed)."""
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def on_start(message: Message) -> None:
        await message.answer(text.WELCOME, reply_markup=main_keyboard())

    @dp.message(Command("help"))
    async def on_help(message: Message) -> None:
        await message.answer(text.HELP)

    @dp.message(Command("game"))
    async def on_game(message: Message) -> None:
        await message.answer_game(game_short_name)

    @dp.callback_query(F.game_short_name == game_short_name)
    async def on_play(callback: CallbackQuery) -> None:
        await callback.answer(url=text.game_link(game_url, callback.from_user.id))

    @dp.message(Command("app"))
    async def on_app(message: Message) -> None:
        await message.answer(text.APP_PROMPT, reply_markup=app_keyboard(web_app_url))

    @dp.callback_query(F.data == "settings")
    async def on_settings(callback: CallbackQuery) -> None:
        await callback.message.edit_text(text.SETTINGS)
        await callback.answer()

    @dp.callback_query(F.data == "help")
    async def on_help_button(callback: CallbackQuery) -> None:
        await callback.message.edit_text(text.HELP)
        await callback.answer()

    @dp.message(F.text & ~F.text.startswith("/"))
    async def on_text(message: Message) -> None:
        await message.answer(text.reply_for(message.text))

    @dp.message(F.text.startswith("/"))
    async def on_unknown(message: Message) -> None:
        await message.answer(text.UNKNOWN)

    return dp
