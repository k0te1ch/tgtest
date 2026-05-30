"""Entry point: ``python -m examples.bot`` (reads BOT_TOKEN from the env).

This is what the E2E test fixture launches as a subprocess. In your own repo
the equivalent would simply be ``python -m bot``.
"""

import asyncio
import os

from aiogram import Bot

from .app import build_dispatcher


async def main() -> None:
    token = os.environ["BOT_TOKEN"]
    bot = Bot(token)
    dp = build_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
