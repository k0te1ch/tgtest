"""Entry point: ``python -m examples.bot`` (reads BOT_TOKEN from the env).

This is what the E2E test fixture launches as a subprocess. In your own repo
the equivalent would simply be ``python -m bot``.
"""

import asyncio
import os

from aiogram import Bot

from . import text
from .app import build_dispatcher


async def main() -> None:
    token = os.environ["BOT_TOKEN"]
    bot = Bot(token)
    dp = build_dispatcher(
        game_short_name=os.environ.get("GAME_SHORT_NAME", text.GAME_SHORT_NAME),
        game_url=os.environ.get("GAME_URL", text.GAME_URL),
        web_app_url=os.environ.get("WEB_APP_URL", text.WEB_APP_URL),
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
