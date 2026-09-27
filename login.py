"""One-time interactive login for the test user account.

Run this once: `python login.py`. Telethon will ask for the code Telegram
sends you (and your 2FA password if enabled), then save an authorized session
file. After that, test runs use the session non-interactively.

`python login.py --string` also prints the session as a string for
TG_SESSION_STRING: no session file, so several clients can use it at once.
"""

import asyncio
import sys

from telethon.sessions import StringSession

from tgtest.client import build_client, connect
from tgtest.config import Settings
from tgtest.exceptions import TgTestError


async def main(print_string: bool) -> None:
    config = Settings.load()
    client = build_client(config)  # honors TG_PROXY, TG_LANG_CODE
    await connect(client, config)  # fails fast with a TG_PROXY hint
    await client.start(phone=config.phone)  # prompts for code/2FA if needed
    me = await client.get_me()
    print(f"Logged in as {me.first_name} (@{me.username}) id={me.id}")
    if not config.session_string:
        print(f"Session saved to: {config.session}")
    if print_string:
        print("TG_SESSION_STRING=" + StringSession.save(client.session))
    await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main(print_string="--string" in sys.argv[1:]))
    except TgTestError as exc:
        sys.exit(f"login failed: {exc}")
