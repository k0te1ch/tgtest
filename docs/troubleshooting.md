# Troubleshooting

## `Session ... is not authorized. Run python login.py once to log in.`

`BotTester.create` connected but the session file has no logged-in user.

- Run `poetry run python login.py` and complete the interactive login.
- Make sure `TG_SESSION` points at the **same** file you logged in with.
- The session file is environment-specific; copy it (securely) to other
  machines/CI rather than re-running interactive login there.

## `TG_API_ID and TG_API_HASH must be set` / config `RuntimeError`

Credentials are missing or unreadable.

- Confirm `.env` exists in the working directory and contains `TG_API_ID` /
  `TG_API_HASH`, or pass `--env path` (CLI) / `Settings.load(env_file=...)`.
- `TG_API_ID` must be an integer.
- Remember these are the **user-client** `api_id`/`api_hash` from
  my.telegram.org — not the bot token.

## `timed out after Ns waiting for a reply`

No message arrived in time.

- Is the **bot actually running** (polling/webhook)? E2E needs a live process —
  see [bot integration](bot-integration.md).
- Is `TG_DEFAULT_BOT` / the scenario `bot:` the correct `@username`?
- For a bot that only replies after **Start**, send `/start` first.
- Genuinely slow step? Raise the timeout: scenario `timeout:`, step `timeout:`,
  or `TG_TIMEOUT`.

## `timed out ... waiting for an edit`

`expect_edit` waits until the **current** message is edited into one that
matches; the error shows the last mismatch (or "the message was not edited").

- If the bot sends a **new** message instead of editing, use `expect` not
  `expect_edit`.
- Confirm the click actually triggered a callback (URL buttons don't call back).
- The result arrives much later (a publish status, a long job)? Use
  `wait_until` with a longer `timeout`: it accepts the message whether or not
  it was already edited.

## `click called before any reply was received`

There is no "current message" yet. Add an `expect` (or `get_reply`) before the
`click` so a message exists to attach the click to.

## `missing buttons [...]` / `buttons differ`

The keyboard didn't match.

- Labels are compared exactly (including emoji/spacing). Print actual labels:
  the failure message lists them.
- Localized or dynamic labels? Click by `data:` (callback data) or `index:`
  instead, and assert text with `contains`/`regex`.
- `buttons_exact` / `exact: true` also checks **order**; use `buttons` for an
  order-free subset check.

## `no bot specified and TG_DEFAULT_BOT is not set`

Set `TG_DEFAULT_BOT` in `.env`, pass `--bot` to the CLI, give the scenario a
`bot:` key, or pass `tester.conversation("@bot")`.

## `ScenarioError: step N must have exactly one action key`

A step needs exactly one action (`send`, `expect`, `click`, …) plus optional
modifiers (`timeout`, `index`, `data`, `exact`, `within`, `note`). You likely
put two actions in one step or misspelled a key. Split into separate steps.

## `FloodWaitError` (from Telethon)

Telegram is rate-limiting the user account (too many requests too fast).

- Add small `sleep` steps; avoid tight loops hammering the bot.
- Don't spin up many connections in parallel against one account.
- Wait out the period Telegram reports.

## `Could not find the input entity for ...` (resolving the bot)

Telethon can't resolve the bot.

- Use the exact `@username` (with the `@`), or a numeric id the account has
  seen.
- Open the bot in Telegram from the test account once so the client knows it.

## E2E tests are skipped

By design when their guard isn't met — e.g. the example skips without
`TEST_BOT_TOKEN`. Provide the required env vars to run them, or that's expected
in offline runs.

## pytest: async tests not running / "coroutine was never awaited"

Ensure `asyncio_mode = "auto"` is set (it is in this project's
`pyproject.toml`) and `pytest-asyncio` is installed. In your own repo, copy the
`[tool.pytest.ini_options]` block.

## Proxy: `ValueError` about the proxy URL at startup

`TG_PROXY` is malformed. It must include a scheme and (for SOCKS/HTTP) a host
and port: `socks5://host:1080`, `http://host:3128`, `mtproxy://SECRET@host:443`.
Percent-encode special characters in credentials (`@` → `%40`). See
[Configuration → Proxy](configuration.md#proxy).

## Proxy: connection hangs or `ProxyError` / cannot connect

- Verify the proxy is reachable and the type matches the scheme (a SOCKS5 proxy
  won't work as `http://`).
- For DNS issues behind the proxy, try `socks5h://` (resolve names via the
  proxy) instead of `socks5://`.
- SOCKS/HTTP support needs `python-socks` installed (it's a dependency; run
  `poetry install`).
- For MTProxy, double-check the `secret` and that the port is the MTProxy port.

## `ConnectError: could not connect to Telegram within Ns`

Telegram did not answer within `TG_CONNECT_TIMEOUT`. On networks where
Telegram data centers are blocked the connection hangs instead of failing, so
set `TG_PROXY` (see [Configuration → Proxy](configuration.md#proxy)). With a
proxy already configured, check that it is reachable. `login.py` fails the
same way instead of hanging.

## `SessionLockedError: Session ... is locked`

Two clients opened the same SQLite session file, typically a test that
creates its own `TelegramClient` next to the `tester` fixture. Use
`tester.client` for the extra steps, or switch to `TG_SESSION_STRING`
(`python login.py --string` prints it), which has no file to lock.

## The bot answers in the wrong language

Bots usually pick the language from `from_user.language_code`. Telegram fills it
from the user's connections, not per message, and tgtest can only influence the
`initConnection` it sends: `TG_LANG_CODE`, `TG_SYSTEM_LANG_CODE` and
`TG_LANG_PACK`.

What is known so far:

- Telethon reports `lang_code="en"` by default and always sends an empty
  `lang_pack` ("language packs are for official apps only").
- A test account that once connected with `lang_code=en` was seen by bots as
  `en` afterwards, and connecting again with `TG_LANG_CODE=ru` did not bring
  `ru` back. So the value sticks to the account (or its authorization) rather
  than following each connection.
- The official apps send a non-empty `lang_pack` (`android`, `ios`,
  `tdesktop`, ...). Setting `TG_LANG_PACK=android` together with
  `TG_LANG_CODE=ru` makes the connection look like theirs; this is the first
  thing to try. It is not verified that Telegram updates `language_code` from it.
- Logging in to the account in an official app with the interface in the wanted
  language, and sending the bot a message from there, resets it the way a real
  user would.

Set the language once, before the first login (`python login.py` honors the
same settings), and keep it the same for every run. Then check what the bot
actually sees instead of assuming it:

```python
async with tester.conversation("@my_bot") as chat:
    lang = await chat.detect_language({"ru": "привет", "en": "hello"})
    if lang != "ru":
        pytest.skip(f"the bot sees the account as {lang!r}, not 'ru'")
```

If the bot under test can be told the language directly (a `/lang` command or a
setting), prefer that in e2e tests: it does not depend on Telegram at all.

## A session file fails with "too many values to unpack"

Telethon 1.43 changed the SQLite session layout; an older Telethon cannot
read a session file that 1.43 has saved. tgtest requires `telethon>=1.43`, so
keep every project that shares the session on 1.43 or newer.

## Where to look

Every run is logged to `logs/tgtest.log` (rotating). Raise detail with
`TG_LOG_LEVEL=DEBUG`.
