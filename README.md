# tgtest — End-to-end testing for Telegram bots

Drives your bots as a **real Telegram user** (via Telethon/MTProto) and asserts
on their replies. Write tests two ways:

- **YAML scenarios** — declarative, fast to write many of, no Python per test.
- **pytest / Python** — full control flow using the same client helpers.

Both run against a live bot through the same engine.

## Why a user account?
The Telegram **Bot API can't receive messages *from* a bot**, so genuine E2E
testing requires a *user* client that sends to your bot and reads its replies.
That's what Telethon provides. You need a (test) user account.

Built on the [python-template](https://github.com/k0te1ch/python-template)
conventions: Poetry, `pydantic-settings`, a rotating-file logger, Ruff,
pre-commit, and GitHub Actions CI.

## Documentation

Full docs live in [`docs/`](docs/README.md):
[Getting started](docs/getting-started.md) ·
[Configuration](docs/configuration.md) ·
[CLI](docs/cli.md) ·
[YAML scenarios](docs/yaml-scenarios.md) ·
[Python API](docs/python-api.md) ·
[Buttons & keyboards](docs/buttons-and-keyboards.md) ·
[Bot integration](docs/bot-integration.md) ·
[Example bot](docs/example-bot.md) ·
[Architecture](docs/architecture.md) ·
[Troubleshooting](docs/troubleshooting.md).

## Setup

1. Install deps (Poetry):
   ```powershell
   poetry install
   ```
2. Get `api_id` / `api_hash` from <https://my.telegram.org> → *API development tools*.
3. Copy `.env.example` to `.env` and fill it in:
   ```
   TG_API_ID=123456
   TG_API_HASH=...
   TG_PHONE=+1...
   TG_SESSION=tgtest.session
   TG_DEFAULT_BOT=@my_bot
   TG_TIMEOUT=15
   TG_LOG_LEVEL=INFO
   # TG_PROXY=socks5://127.0.0.1:9050   # optional; socks5/socks4/http/mtproxy
   ```
   Settings are loaded via `pydantic-settings` (`tgtest/config.py`); every
   variable uses the `TG_` prefix. Behind a proxy? See
   [docs/configuration.md → Proxy](docs/configuration.md#proxy).
4. Log in **once** (interactive — enter the code Telegram sends, plus 2FA if set):
   ```powershell
   poetry run python login.py
   ```
   This writes an authorized `*.session` file. Test runs reuse it
   non-interactively. **Never commit `.env` or `*.session`** (already gitignored).

## Running YAML scenarios

```powershell
poetry run tgtest run scenarios/               # a directory (recursive)
poetry run tgtest run scenarios/example_start.yaml
poetry run tgtest run "scenarios/*.yaml" --bot @other_bot
# equivalent: python -m tgtest run ...   /   python main.py run ...
```

Runs are logged to `logs/tgtest.log` (rotating). Exit code is non-zero if any
scenario fails (CI-friendly). Output is per scenario `PASS` / `FAIL` with the
exact failing step and a diff-style reason.

### Scenario format

A `.yaml` file holds one or more scenarios (separate with `---`):

```yaml
name: Start command shows main menu
bot: "@my_bot"        # optional → falls back to TG_DEFAULT_BOT
timeout: 15            # optional default per-step reply timeout (seconds)
steps:
  - command: start              # sends "/start" (adds the "/" for you)
  - expect:                     # wait for next reply, assert on it
      contains: "Welcome"
      buttons: ["Settings", "Help"]
  - click: "Settings"           # press an inline button by label
  - expect_edit:                # bot edited the message in place
      icontains: "settings"
  - send: "ping"                # plain text
  - expect:
      regex: "^pong"
```

#### Step actions

| Step | Meaning |
|------|---------|
| `send: <text>` | Send a plain text message. |
| `command: <name>` | Send a `/command` (leading `/` optional). |
| `expect: <matcher>` | Wait for the next reply and assert on it. |
| `expect_edit: <matcher>` | Wait for the current message to be edited, then assert. |
| `expect_buttons: [..]` | Assert the current message shows these buttons (add `exact: true` for full match). |
| `expect_no_reply: <sec>` | Assert nothing arrives within N seconds. |
| `click: <label>` | Click an inline button by label (or `click:` with `index:` / `data:`). |
| `sleep: <sec>` | Pause. |

Any step may carry a `timeout:` (override) and a `note:` (shown in reports).

#### Matchers (used by `expect` / `expect_edit`)

A matcher is a string (shorthand for `equals`) or a mapping of:

- `equals`, `contains`, `icontains` (case-insensitive), `not_contains`
- `regex`, `iregex` (case-insensitive)
- `buttons: [..]` (all must be present), `buttons_exact: [..]` (whole keyboard, in order)
- `has_buttons: true|false`

Multiple clauses in one `expect` must **all** pass.

## Running pytest / Python tests

`tests/conftest.py` already enables the plugin. Write async tests using the
`tester` fixture (a connected client) or `run_yaml` (run scenario files):

```python
import pytest

@pytest.mark.live
async def test_start(tester):
    async with tester.conversation("@my_bot") as chat:
        await chat.send("/start")
        await chat.expect(contains="Welcome", buttons=["Settings"])
        await chat.click("Settings")
        await chat.expect_edit(icontains="settings")

@pytest.mark.live
async def test_via_yaml(run_yaml):
    await run_yaml("scenarios/example_start.yaml")
```

```powershell
poetry run pytest                 # run everything
poetry run pytest -m "not live"   # skip tests that hit a real bot (what CI runs)
```

Unit tests for the matchers, scenario parser, and config are **not** marked
`live`, so they run in CI without credentials.

### `_Chat` helper API
`send`, `command`, `get_reply`, `expect(**matcher)`, `expect_edit(**matcher)`,
`expect_no_reply(within=)`, `expect_buttons(*labels, exact=)`,
`click(text=/index=/data=)`. `chat.last` is the most recent `Message`.

## Using tgtest inside a bot project (next to unit tests)

Your bot repo keeps its **unit tests** (fast, no network) and adds **E2E tests**
that drive the real bot through tgtest. Keep the two apart with a pytest marker
so the fast suite stays the default and the slow live suite is opt-in.

The crucial difference: unit tests need nothing external; **E2E needs the bot
process actually running** (polling or webhook) so it can answer the user
client. The recipe below starts the bot for you.

> A complete, runnable version of everything in this section lives in
> [`examples/`](examples/README.md): a tiny aiogram bot with unit tests and
> tgtest E2E tests (including the bot-launch fixture). `python -m pytest
> examples/tests/unit` runs with zero setup.

### 1. Add tgtest as a dev dependency of the bot

In the bot's `pyproject.toml` (Poetry) — git or local path:

```toml
[tool.poetry.group.dev.dependencies]
tgtest = { git = "https://github.com/you/TelegramTests.git" }
# while iterating locally, a path dependency is handy instead:
# tgtest = { path = "../TelegramTests", develop = true }
```

(pip equivalent: `pip install git+https://github.com/you/TelegramTests.git`
or `pip install -e ../TelegramTests`.)

### 2. Recommended layout in the bot repo

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

### 3. Enable the plugin and separate the markers

`tests/conftest.py`:

```python
pytest_plugins = ["tgtest.pytest_plugin"]   # gives you tester / run_yaml / tg_config
```

`pyproject.toml` of the bot repo — make unit the default, E2E opt-in:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["e2e: live test that talks to the running bot"]
addopts = "-m 'not e2e'"     # default `pytest` run = unit only
```

(The marker name is yours; this platform's own examples happen to use `live`.)

### 4. Start the bot during E2E

`tests/e2e/conftest.py` — launch the bot as a subprocess once per session and
shut it down afterward:

```python
import os
import subprocess
import time

import pytest


@pytest.fixture(scope="session")
def bot_process():
    # ALWAYS a dedicated test bot token, never production.
    env = {**os.environ, "BOT_TOKEN": os.environ["TEST_BOT_TOKEN"]}
    proc = subprocess.Popen(["python", "-m", "bot"], env=env)
    try:
        time.sleep(3)                       # let it connect / start polling
        assert proc.poll() is None, "bot exited during startup"
        yield proc
    finally:
        proc.terminate()
        proc.wait(timeout=10)
```

Depend on it so the bot is up before the user client talks to it:

```python
import pytest


@pytest.mark.e2e
async def test_start(bot_process, tester):
    async with tester.conversation("@my_test_bot") as chat:
        await chat.send("/start")
        await chat.expect(contains="Welcome")


@pytest.mark.e2e
async def test_via_yaml(bot_process, run_yaml):
    await run_yaml("tests/e2e/scenarios/start.yaml")
```

> **Readiness:** a fixed `sleep` is the simplest gate and fine for polling bots.
> For webhook bots, instead wait until the port is open or a "started" line
> appears in the bot's stdout/log — more reliable than sleeping.

### 5. Run them

```powershell
poetry run pytest                    # fast: unit only (addopts excludes e2e)
poetry run pytest -m e2e             # the live end-to-end suite (overrides addopts)
poetry run pytest -o addopts=""      # everything (clears the default -m filter)
```

### 6. CI: two jobs

- **unit** — every push / PR, no secrets: `pytest -m "not e2e"`.
- **e2e** — gated (nightly, manual, or protected branch). Provide `TG_API_ID`,
  `TG_API_HASH`, `TEST_BOT_TOKEN`, and a pre-made session as CI secrets; the job
  starts the bot and runs `pytest -m e2e`.

A session **can't be created interactively in CI**. Generate it once locally
(`python login.py`), then restore it in the job from a base64 secret — or run
E2E only locally / on a self-hosted runner.

### Safety

- Use a **separate test bot** and a **separate test user account** — never a
  production token or your personal account.
- Tests send real messages; talk to the bot in a dedicated test chat.

## Layout

```
tgtest/            the package
  config.py        Settings(BaseSettings) — env/.env loading (TG_ prefix)
  logger.py        rotating-file logger (logs/tgtest.log)
  client.py        BotTester + _Chat (Telethon Conversation wrapper)
  matchers.py      text/button matchers
  scenario.py      YAML → Scenario model
  engine.py        runs a Scenario against a chat
  cli.py           `tgtest run ...` entry point
  pytest_plugin.py fixtures: tg_config, tester, run_yaml
main.py            entry point (delegates to the CLI)
login.py           one-time interactive login
scenarios/         your YAML scenarios (example included)
tests/             pytest tests (unit + live examples)
examples/          runnable reference bot (aiogram) with unit + E2E tests
logs/              rotating run logs (gitignored)
pyproject.toml     Poetry project + Ruff + pytest config
.pre-commit-config.yaml, .github/workflows/  lint + CI
```

## Dev tooling

```powershell
poetry run ruff check .              # lint (E/F/W/C90/B/N, line-length 88)
poetry run pre-commit run --all-files
```
