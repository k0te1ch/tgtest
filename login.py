"""One-time interactive login for the test user account.

Run this once: `python login.py`. Telethon will ask for the code Telegram
sends you (and your 2FA password if enabled), then save an authorized session
file. After that, test runs use the session non-interactively.
"""

import asyncio

from tgtest.client import build_client
from tgtest.config import Settings


async def main():
    config = Settings.load()
    client = build_client(config)  # honors TG_PROXY if set
    await client.start(phone=config.phone)  # prompts for code/2FA if needed
    me = await client.get_me()
    print(f"Logged in as {me.first_name} (@{me.username}) id={me.id}")
    print(f"Session saved to: {config.session}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
