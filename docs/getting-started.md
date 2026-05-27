# Getting started

## 1. Requirements

- Python 3.12+
- [Poetry](https://python-poetry.org/) (the project's package manager)
- A **Telegram user account** for the test client (ideally a dedicated one).
- The bot you want to test (ideally a dedicated test bot).

## 2. Install

```powershell
poetry install
```

This installs the runtime deps (Telethon, PyYAML, python-dotenv,
pydantic-settings) and dev tools (pytest, ruff, pre-commit). To also run the
reference bot under [`examples/`](example-bot.md):

```powershell
poetry install --with examples
```

## 3. Get API credentials

1. Sign in at <https://my.telegram.org> with the **test user account**.
2. Open *API development tools* and create an app.
3. Copy the `api_id` (an integer) and `api_hash` (a hex string).

These identify the *user client*, not the bot. They are not the bot token.

## 4. Configure `.env`

Copy `.env.example` to `.env` and fill it in:

```
TG_API_ID=123456
TG_API_HASH=0123456789abcdef0123456789abcdef
TG_PHONE=+10000000000
TG_SESSION=tgtest.session
TG_DEFAULT_BOT=@my_bot
TG_TIMEOUT=15
TG_LOG_LEVEL=INFO
```

See [Configuration](configuration.md) for every variable. **Never commit `.env`
or the `*.session` file** — both are gitignored.

## 5. Log in once

```powershell
poetry run python login.py
```

Telethon asks for the login code Telegram sends to the account (and your 2FA
password if you have one), then writes an authorized session file
(`tgtest.session` by default). From then on, test runs reuse it
**non-interactively** — the runner never prompts, so it works in automation.

> The session file *is* a credential. Treat it like a password.

## 6. Make sure the bot can be reached

For the user client to talk to a bot:

- The bot must exist and be **running** (long polling or webhook) if you expect
  live replies.
- `TG_DEFAULT_BOT` (or a scenario's `bot:`) must be the bot's `@username` (or a
  numeric id / invite the client can resolve).
- Some bots only respond after the user has pressed **Start** once; sending
  `/start` from the client does this.

## 7. Run your first test

YAML:

```powershell
poetry run tgtest run scenarios/example_start.yaml
```

pytest:

```powershell
poetry run pytest                 # everything (live tests included)
poetry run pytest -m "not live"   # only the offline unit tests
```

Next: [YAML scenarios](yaml-scenarios.md) or the [Python API](python-api.md).
