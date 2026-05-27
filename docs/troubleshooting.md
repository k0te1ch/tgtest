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

`expect_edit` expects the **current** message to be edited, but it wasn't.

- If the bot sends a **new** message instead of editing, use `expect` not
  `expect_edit`.
- Confirm the click actually triggered a callback (URL buttons don't call back).

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

## Where to look

Every run is logged to `logs/tgtest.log` (rotating). Raise detail with
`TG_LOG_LEVEL=DEBUG`.
