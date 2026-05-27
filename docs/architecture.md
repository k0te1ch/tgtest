# Architecture

How tgtest is put together and why.

## Big picture

```
        YAML files                     pytest tests
            │                                │
            ▼                                ▼
   scenario.py  ──►  engine.py  ──►  client.py (BotTester / _Chat)
   (parse+validate)  (run steps)         │
                          │              ▼
                     matchers.py     Telethon (MTProto, user account)
                     (assertions)         │
                                          ▼
                                    Telegram  ◄──►  your bot
```

A user-account client sends to the bot and reads replies; the engine turns
declarative steps into client calls; matchers turn replies into pass/fail.

## Modules

| Module | Responsibility |
|--------|----------------|
| [`config.py`](../tgtest/config.py) | `Settings` (pydantic-settings) — load + validate `TG_*` config. |
| [`logger.py`](../tgtest/logger.py) | Rotating-file logger (`logs/tgtest.log`). |
| [`client.py`](../tgtest/client.py) | `BotTester` (owns the connection) and `_Chat` (per-bot helpers). |
| [`matchers.py`](../tgtest/matchers.py) | `Matcher` — text/button assertions; returns a reason string or `None`. |
| [`scenario.py`](../tgtest/scenario.py) | Parse + validate YAML into `Scenario`/`Step` models. |
| [`engine.py`](../tgtest/engine.py) | Execute a `Scenario` against a `_Chat`; wrap failures in `StepError`. |
| [`cli.py`](../tgtest/cli.py) | `tgtest run` — discovery, execution, reporting, exit codes. |
| [`pytest_plugin.py`](../tgtest/pytest_plugin.py) | Fixtures: `tg_config`, `tester`, `run_yaml`. |
| [`exceptions.py`](../tgtest/exceptions.py) | `TgTestError` ⊃ `ScenarioError`, `StepError`. |

## Why Telethon and a user account

The Bot API only lets a bot *receive* updates and *send* messages; it cannot
observe what another bot sends. End-to-end testing needs the *other side* of the
chat — a human-like client. Telethon implements MTProto and can log in as a user
account, so it can message your bot and read replies, edits, and keyboards.

## The `Conversation` foundation

`_Chat` wraps Telethon's
[`client.conversation()`](https://docs.telethon.dev/en/stable/modules/client.html#telethon.client.dialogs.DialogMethods.conversation),
which provides ordered, timeout-aware access to one chat:

- `conv.send_message(...)` — send.
- `conv.get_response(timeout=)` — next incoming message (powers `get_reply` /
  `expect`).
- `conv.get_edit(message, timeout=)` — wait for a specific message to be edited
  (powers `expect_edit`).
- `message.click(...)` — click inline/reply buttons (powers `click`).

Using `Conversation` (rather than raw event handlers) gives deterministic,
in-order reads with per-step timeouts — ideal for assertions.

## The "current message" model

`_Chat.last` tracks the most recent reply. `expect` / `expect_edit` advance it;
`click`, `expect_buttons`, and `expect_edit` act on it. This mirrors how a user
reads the latest message and interacts with it, and keeps scenarios linear and
readable.

## Matchers as reason-returning functions

`Matcher.check(message)` returns `None` on success or a human-readable reason on
failure (instead of raising). The caller composes one rich error with full
context (which clause failed, expected vs actual). This keeps assertion logic
shared between the YAML engine and the Python API.

## Error model

- Parse-time problems → `ScenarioError` (CLI exit 2) before any network call.
- Assertion / timeout during a step → `AssertionError`, wrapped by the engine
  into `StepError(step_index, step_desc)` for precise reporting.
- Unauthorized session → `RuntimeError` from `BotTester.create` (run
  `login.py`).

## Connection lifecycle

`BotTester.create()` connects once and disconnects on exit. The pytest `tester`
fixture is function-scoped (one connection per test) for isolation; the CLI
opens one connection and runs all scenarios through it.

Both `BotTester.create()` and `login.py` build the underlying client via the
shared `build_client(config)` helper, which applies `TG_PROXY` (parsed by
[`proxy.py`](../tgtest/proxy.py)) so test runs and first-time login use the
same proxy. See [Configuration → Proxy](configuration.md#proxy).
