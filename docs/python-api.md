# Python API

For tests that need real control flow (loops, conditionals, computed
assertions), drive the bot from Python. The same engine and helpers power both
YAML and Python tests.

Sources: [`tgtest/client.py`](../tgtest/client.py),
[`tgtest/pytest_plugin.py`](../tgtest/pytest_plugin.py),
[`tgtest/__init__.py`](../tgtest/__init__.py).

## Top-level imports

```python
from tgtest import (
    Settings, configure_logger,
    BotTester, ReplyMatchError,
    Scenario, load_scenario, load_scenarios, run_scenario,
    TgTestError, ScenarioError, StepError,
)
```

## `BotTester`

Owns the Telethon connection and hands out per-bot conversations.

```python
import asyncio
from tgtest import Settings, BotTester

async def main():
    config = Settings.load()
    async with BotTester.create(config) as tester:
        async with tester.conversation("@my_bot") as chat:
            await chat.send("/start")
            await chat.expect(contains="Welcome", buttons=["Settings"])
            await chat.click("Settings")
            await chat.expect_edit(icontains="settings")

asyncio.run(main())
```

- `BotTester.create(config)` — async context manager. Connects using the
  existing session; **raises `RuntimeError` if the session is not authorized**
  (run `python login.py` first). It never prompts, so it is safe in automation.
- `tester.conversation(bot=None, timeout=None)` — async context manager
  yielding a `_Chat`. `bot` defaults to `TG_DEFAULT_BOT`; `timeout` defaults to
  `TG_TIMEOUT`.

## `_Chat` — the conversation helper

`chat.last` holds the most recently received `Message` (the "current message").

### Sending

| Method | Description |
|--------|-------------|
| `await chat.send(text)` | Send literal text. |
| `await chat.command(cmd)` | Send a `/command` (adds the `/` if missing). |

### Receiving & asserting

| Method | Description |
|--------|-------------|
| `await chat.get_reply(timeout=None)` | Wait for and return the next reply; sets `chat.last`. |
| `await chat.expect(timeout=None, **matcher)` | `get_reply` + assert; returns the message. |
| `await chat.expect_edit(timeout=None, **matcher)` | Wait for `chat.last` to be edited, then assert. |
| `await chat.expect_no_reply(within=2.0)` | Assert nothing arrives within `within` seconds. |
| `chat.expect_buttons(*labels, exact=False)` | Assert the current message's buttons (sync). |

The `**matcher` keyword arguments are exactly the [matcher
clauses](yaml-scenarios.md#matchers): `equals`, `contains`, `icontains`,
`not_contains`, `regex`, `iregex`, `buttons`, `buttons_exact`, `has_buttons`.

```python
await chat.expect(contains="Welcome", buttons=["Settings", "Help"])
await chat.expect(regex=r"#\d+", has_buttons=True)
```

### Interacting

| Method | Description |
|--------|-------------|
| `await chat.click(text="Label")` | Click an inline button by visible label. |
| `await chat.click(index=0)` | Click by 0-based position. |
| `await chat.click(data="cb")` | Click by callback `data`. |

See [Buttons & keyboards](buttons-and-keyboards.md) for full semantics.

## Assertions & exceptions

- Failed assertions raise `AssertionError` (exported as `ReplyMatchError`), so
  they integrate naturally with pytest.
- `run_scenario(tester, scenario)` wraps failures in `StepError`, carrying
  `step_index` and `step_desc`.
- Exception hierarchy: `TgTestError` ⊃ `ScenarioError`, `StepError`.

## pytest fixtures

Enable the plugin in your `conftest.py`:

```python
pytest_plugins = ["tgtest.pytest_plugin"]
```

| Fixture | Scope | What it gives you |
|---------|-------|-------------------|
| `tg_config` | session | A loaded `Settings`. |
| `tester` | function | A connected `BotTester` (one connection per test). |
| `run_yaml` | function | `async` callable: `await run_yaml("path.yaml", ...)`. |

```python
import pytest

@pytest.mark.live
async def test_start(tester):
    async with tester.conversation("@my_bot") as chat:
        await chat.send("/start")
        await chat.expect(contains="Welcome")

@pytest.mark.live
async def test_scenarios(run_yaml):
    await run_yaml("scenarios/start.yaml")
```

Tests are `async`; the project sets `asyncio_mode = "auto"` so no per-test
decorator is needed. Mark tests that hit a real bot (e.g. `live` / `e2e`) so
they can be excluded from offline runs: `pytest -m "not live"`.

## Running scenarios programmatically

```python
from tgtest import load_scenarios, run_scenario, BotTester, Settings

scenarios = load_scenarios(["scenarios/"])
async with BotTester.create(Settings.load()) as tester:
    for sc in scenarios:
        await run_scenario(tester, sc)   # raises StepError on first failure
```
