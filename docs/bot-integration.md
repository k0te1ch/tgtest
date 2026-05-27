# Using tgtest with your bot (next to unit tests)

This guide shows how to put tgtest **end-to-end tests inside your bot's own
repository**, alongside its fast unit tests, and run them in CI.

A complete, runnable version of everything here lives in
[`examples/`](example-bot.md).

## The core difference

| | Unit tests | E2E tests (tgtest) |
|--|-----------|--------------------|
| Needs network / Telegram | no | **yes** |
| Needs the bot running | no | **yes** (polling or webhook) |
| Speed | milliseconds | seconds |
| Default in CI | always | gated / opt-in |

Because E2E needs the bot **process actually running** so it can answer the
user client, you launch it for the duration of the live test session and tear
it down after. Keep the two suites apart with a pytest **marker** so the fast
suite stays the default.

## 1. Add tgtest as a dev dependency

In your bot's `pyproject.toml` (Poetry):

```toml
[tool.poetry.group.dev.dependencies]
tgtest = { git = "https://github.com/you/TelegramTests.git" }
# local path while iterating:
# tgtest = { path = "../TelegramTests", develop = true }
```

pip equivalents: `pip install git+https://github.com/you/TelegramTests.git`
or `pip install -e ../TelegramTests`.

## 2. Recommended layout

```
my_bot/
  bot/                    your bot code (entry point: python -m bot)
  tests/
    conftest.py           enables the tgtest plugin
    unit/                 fast unit tests (no Telegram)
    e2e/
      conftest.py         the "start the bot" fixture
      test_start.py       live tests
      scenarios/          optional YAML scenarios
  .env                    TG_* creds for the TEST user account
  pyproject.toml
```

Split your bot like the example does: put **pure logic and copy in a
framework-free module** (unit-tested), and keep the framework wiring thin
(exercised by E2E). This is what lets both suites coexist cleanly.

## 3. Enable the plugin and separate markers

`tests/conftest.py`:

```python
pytest_plugins = ["tgtest.pytest_plugin"]
```

`pyproject.toml` — make unit the default, E2E opt-in:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["e2e: live test that talks to the running bot"]
addopts = "-m 'not e2e'"     # default `pytest` run = unit only
```

The marker name is yours; this platform's own examples use `live`.

## 4. Start the bot during E2E

`tests/e2e/conftest.py`:

```python
import os
import subprocess
import sys
import time

import pytest


@pytest.fixture(scope="session")
def bot_process():
    token = os.environ.get("TEST_BOT_TOKEN")
    if not token:
        pytest.skip("TEST_BOT_TOKEN not set; skipping live E2E")
    env = {**os.environ, "BOT_TOKEN": token}
    proc = subprocess.Popen([sys.executable, "-m", "bot"], env=env)
    try:
        time.sleep(3)                       # let it start polling
        if proc.poll() is not None:
            raise RuntimeError("bot exited during startup")
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
```

Depend on it so the bot is up before the user client talks to it:

```python
import pytest

@pytest.mark.e2e
async def test_start(bot_process, tester):
    async with tester.conversation("@my_test_bot") as chat:
        await chat.send("/start")
        await chat.expect(contains="Welcome")
```

> **Readiness.** A fixed `sleep` is the simplest gate and fine for polling bots.
> For webhook bots, wait until the port is open or a "started" line appears in
> the bot's stdout/log instead of sleeping — it's more reliable.

## 5. Run them

```powershell
pytest                    # fast: unit only (addopts excludes e2e)
pytest -m e2e             # the live end-to-end suite (overrides addopts)
pytest -o addopts=""      # everything (clears the default -m filter)
```

## 6. CI: two jobs

- **unit** — every push / PR, no secrets: `pytest -m "not e2e"`.
- **e2e** — gated (nightly, manual, or protected branch). Provide `TG_API_ID`,
  `TG_API_HASH`, `TEST_BOT_TOKEN`, and a pre-made session as CI secrets; the
  job starts the bot and runs `pytest -m e2e`.

A session **cannot be created interactively in CI**. Generate it once locally
(`python login.py`), then restore it in the job from a base64 secret — or run
E2E only locally / on a self-hosted runner.

## Safety

- Use a **separate test bot** and a **separate test user account** — never a
  production token or your personal account.
- Tests send real messages; talk to the bot in a dedicated test chat.
