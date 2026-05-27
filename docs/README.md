# tgtest documentation

End-to-end testing for Telegram bots. tgtest acts as a **real Telegram user**
(via [Telethon](https://docs.telethon.dev) / MTProto), sends messages to your
bot, clicks its buttons, and asserts on the replies — either through declarative
**YAML scenarios** or **pytest/Python** tests, both run by the same engine.

## Contents

1. [Getting started](getting-started.md) — install, credentials, first login, first test.
2. [Configuration](configuration.md) — `Settings`, the `TG_` environment variables, `.env`.
3. [CLI](cli.md) — `tgtest run`, flags, exit codes.
4. [YAML scenarios](yaml-scenarios.md) — full step + matcher reference.
5. [Python API](python-api.md) — `BotTester`, the `_Chat` helpers, pytest fixtures, exceptions.
6. [Buttons & keyboards](buttons-and-keyboards.md) — clicking inline buttons, asserting keyboards.
7. [Using tgtest with your bot](bot-integration.md) — next to unit tests, project layout, CI.
8. [The example bot](example-bot.md) — walkthrough of `examples/`.
9. [Architecture](architecture.md) — how it works under the hood.
10. [Troubleshooting](troubleshooting.md) — common errors and fixes.

## Why a user account?

The Telegram **Bot API cannot receive messages *from* a bot**. To test a bot
end-to-end you need a client that plays the role of a human user: it sends to
the bot and reads what comes back. That client is a *user account* driven by
Telethon over MTProto. You therefore need a (preferably dedicated, test-only)
Telegram user account plus its `api_id` / `api_hash`.

## 60-second tour

```powershell
poetry install
# fill .env with TG_API_ID / TG_API_HASH / TG_PHONE / TG_DEFAULT_BOT
poetry run python login.py            # one-time interactive login
poetry run tgtest run scenarios/      # run YAML scenarios
poetry run pytest -m "not live"       # run the offline unit tests
```

```yaml
# scenarios/start.yaml
name: Start shows the menu
steps:
  - command: start
  - expect:
      contains: "Welcome"
      buttons: ["Settings", "Help"]
  - click: "Settings"          # click an inline button
  - expect_edit:
      icontains: "settings"
```
