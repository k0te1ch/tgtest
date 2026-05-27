# The example bot

[`examples/`](../examples/) contains a minimal [aiogram](https://docs.aiogram.dev)
bot wired exactly the way [Using tgtest with your bot](bot-integration.md)
describes — a runnable reference you can copy.

## Files

```
examples/
  bot/
    text.py        pure logic + copy (NO aiogram import) -> unit tested
    app.py         aiogram handlers, built from text.py
    __main__.py    `python -m examples.bot` (reads BOT_TOKEN) -> what E2E launches
  tests/
    conftest.py    enables the tgtest plugin
    unit/          fast, no network, no aiogram runtime, no Telegram
    e2e/
      conftest.py  starts the bot as a subprocess for the live session
      test_bot_e2e.py
      scenarios/   the same flow as a YAML scenario
```

The split that makes both test kinds coexist: decision logic and message text
live in `text.py` **with no framework import**, so unit tests load only that;
`app.py` wires it into handlers, and that wiring is what E2E exercises against a
real running bot. The package `examples/bot/__init__.py` deliberately does not
import `app.py`, keeping `from examples.bot import text` aiogram-free.

## Bot behaviour

- `/start` → "Welcome…" with inline buttons **Settings** / **Help**
- press **Settings** → the message is edited in place to the settings text
- `ping` → `pong`; any other text → `You said: …`
- unknown `/command` → "Unknown command."

## Run the unit tests (no setup)

```powershell
python -m pytest examples/tests/unit
```

No credentials, token, or aiogram runtime needed — they import only
`examples.bot.text`.

## Run the E2E tests (live)

1. Install the bot framework: `poetry install --with examples`.
2. Create a **dedicated test bot** (@BotFather) and a **test user account**;
   set in `.env`:
   ```
   TEST_BOT_TOKEN=123:abc
   TG_DEFAULT_BOT=@my_test_bot
   TG_API_ID=...
   TG_API_HASH=...
   TG_SESSION=tgtest.session
   ```
3. Authorize the user client once: `poetry run python login.py`.
4. Run only the live suite (the fixture starts the bot for you):
   ```powershell
   python -m pytest examples/tests/e2e -m e2e
   ```

If `TEST_BOT_TOKEN` is unset, the E2E tests **skip** rather than fail, so the
example is safe to leave in the repo.

> The top-level `pyproject.toml` sets `testpaths = ["tests"]`, so a bare
> `pytest` runs the **platform's** tests, not the example. Pass the example
> path explicitly as shown above.
