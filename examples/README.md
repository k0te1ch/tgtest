# Example: a bot with unit tests + tgtest E2E

A minimal [aiogram](https://docs.aiogram.dev) bot wired exactly the way the
top-level README's *"Using tgtest inside a bot project"* section describes — a
working reference you can copy into your own repo.

## What's here

```
examples/
  bot/
    text.py        pure logic + copy (NO aiogram import) -> unit tested
    app.py         aiogram handlers, built from text.py
    __main__.py    `python -m examples.bot` (reads BOT_TOKEN) -> what E2E launches
  tests/
    conftest.py    enables the tgtest plugin
    unit/          fast, no network, no aiogram-runtime, no Telegram
    e2e/
      conftest.py  starts the bot as a subprocess for the live session
      test_bot_e2e.py
      scenarios/   the same flow as a YAML scenario
```

The key trick: **decision logic lives in `text.py` with no framework import**,
so unit tests run anywhere; `app.py` only wires it into handlers, and that wiring
is what the E2E tests exercise against a real running bot.

## Bot behaviour

- `/start` → "Welcome..." with inline buttons **Settings** / **Help**
- press **Settings** → message is edited in place to the settings text
- `ping` → `pong`; any other text → `You said: ...`
- unknown `/command` → "Unknown command."

## Run the unit tests (no setup)

```powershell
python -m pytest examples/tests/unit
```

These don't need credentials, a token, or even aiogram's runtime — they import
only `examples.bot.text`.

## Run the E2E tests (live)

1. Install the example's bot framework:
   ```powershell
   poetry install --with examples
   ```
2. Create a **dedicated test bot** with @BotFather and a **test user account**;
   set in your environment / `.env`:
   ```
   TEST_BOT_TOKEN=123:abc        # the test bot's token (BotFather)
   TG_DEFAULT_BOT=@my_test_bot    # that bot's @username
   TG_API_ID=...                  # user-client creds (my.telegram.org)
   TG_API_HASH=...
   TG_SESSION=tgtest.session
   ```
3. Authorize the user client once: `poetry run python login.py`.
4. Run only the live suite (the bot is started for you by the fixture):
   ```powershell
   python -m pytest examples/tests/e2e -m e2e
   ```

If `TEST_BOT_TOKEN` is unset the E2E tests **skip** rather than fail, so the
example is safe to leave in a repo.

> The top-level `pyproject.toml` sets `testpaths = ["tests"]`, so a bare
> `pytest` in this repo runs the **platform's** tests, not the example. Pass the
> example path explicitly as shown above.
