"""aiogram wiring for the demo bot. Pure logic lives in ``text.py``."""
from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from . import text


def main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for label, data in text.main_menu():
        builder.button(text=label, callback_data=data)
    builder.adjust(2)
    return builder.as_markup()


def build_dispatcher() -> Dispatcher:
    """Build a Dispatcher with all handlers registered (no Bot/token needed)."""
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def on_start(message: Message) -> None:
        await message.answer(text.WELCOME, reply_markup=main_keyboard())

    @dp.message(Command("help"))
    async def on_help(message: Message) -> None:
        await message.answer(text.HELP)

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
