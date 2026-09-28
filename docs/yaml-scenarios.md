# YAML scenarios

A scenario is a declarative list of steps executed in order against one bot.
Scenarios are the fastest way to write many tests without Python.

Sources: [`tgtest/scenario.py`](../tgtest/scenario.py) (parser),
[`tgtest/engine.py`](../tgtest/engine.py) (executor),
[`tgtest/matchers.py`](../tgtest/matchers.py) (matchers).

## File structure

```yaml
name: Start command shows main menu   # label used in reports
bot: "@my_bot"                          # optional → falls back to TG_DEFAULT_BOT
timeout: 15                             # optional default per-step reply timeout (s)
steps:
  - command: start
  - expect:
      contains: "Welcome"
```

Top-level keys:

| Key | Required | Meaning |
|-----|----------|---------|
| `name` | no (defaults to file name) | Human label shown in results. |
| `bot` | no | Target bot `@username` / id. Falls back to `TG_DEFAULT_BOT`. |
| `timeout` | no | Default reply timeout for every step (seconds). |
| `steps` | **yes** | Ordered list of step mappings. |

### Multiple scenarios per file

Separate documents with `---`; one file then holds a whole suite:

```yaml
name: First
steps:
  - send: a
---
name: Second
steps:
  - send: b
```

### What `run` accepts

`tgtest run` (and `run_yaml(...)`) take files, directories (searched
recursively for `*.yaml`/`*.yml`), and globs.

## Execution model

The engine opens one conversation with the bot, then walks the steps top to
bottom. There is a notion of the **current message**: the most recent reply
received. `expect` / `expect_edit` advance it; `click`, `expect_buttons`, and
`expect_edit` operate on it. The first failing step aborts the scenario and is
reported with its index and description.

## Steps

Each step is a mapping with **exactly one action key**, plus optional modifier
keys.

| Action | Value | Notes |
|--------|-------|-------|
| `send` | string | Send literal text. |
| `send_file` | path | Send a file (audio, photo, document...). |
| `command` | string | Send a `/command`; the leading `/` is added if missing. |
| `expect` | matcher | Wait for the next reply, make it current, assert on it. |
| `expect_edit` | matcher | Wait until the **current** message is edited into one that matches. |
| `wait_until` | matcher | Wait until the current message matches, edited or not (late results). |
| `expect_no_reply` | seconds (number) | Assert nothing arrives within N seconds. |
| `expect_buttons` | string or list | Assert the current message exposes these button labels. |
| `click` | string (label) or empty | Click an inline button on the current message. |
| `sleep` | seconds (number) | Pause. |
| `play` | empty | Press the game button of the last game message; the bot must answer with a URL. |
| `expect_game_score` | score (number) or empty | Wait for the next score message of the last game (posted after the bot's `setGameScore`). |
| `open_web_app` | string (label) | Open a `web_app` button of the current message (inline or reply keyboard). |
| `open_menu_app` | empty | Open the Mini App behind the bot's menu button. |
| `open_app` | string (short name) | Open the named Mini App `t.me/<bot>/<short_name>`. |

### Modifier keys

These may accompany any action:

| Modifier | Applies to | Meaning |
|----------|-----------|---------|
| `timeout` | `expect`, `expect_edit`, `wait_until` | Override the reply timeout (seconds) for this step. |
| `exact` | `expect_buttons` | Require the keyboard to match exactly (set + order). |
| `index` | `click` | Click the button at this 0-based position. |
| `data` | `click` | Click the button with this callback `data`. |
| `within` | `expect_no_reply` | Alternative to the inline value. |
| `caption` | `send_file` | Caption for the file. |
| `force_document` | `send_file` | Send as a document instead of media. |
| `url_contains` | `play`, `open_*` | The returned URL must contain this substring. |
| `url_regex` | `play`, `open_*` | `re.search` must find this pattern in the returned URL. |
| `page_loads` | `play`, `open_*` | `true` opens the URL in a headless browser (needs the `browser` extra). |
| `start_param` | `open_app` | Start parameter passed to the Mini App. |
| `min_score` | `expect_game_score` | The score must be at least this. |
| `note` | any | Free-text shown in failure reports. |

### Step examples

```yaml
steps:
  - command: start                 # -> "/start"
  - send: "ping"

  - expect:                        # wait + assert text and buttons together
      contains: "Welcome"
      buttons: ["Settings", "Help"]

  - click: "Settings"              # by visible label
  - click:                         # by position
      index: 0
  - click:                         # by callback data
      data: "settings"

  - expect_edit:                   # bot edited the message after the click
      icontains: "settings"

  - expect_buttons: ["Back"]       # assert current keyboard
  - expect_buttons: ["A", "B"]     # exact match
    exact: true

  - expect_no_reply: 3             # nothing for 3 seconds
  - sleep: 1

  - expect:                        # per-step timeout override + a note
      regex: "^Done"
    timeout: 30
    note: "slow report generation"
```

See [Buttons & keyboards](buttons-and-keyboards.md) for the click semantics
and [Games & Mini Apps](games-and-mini-apps.md) for the game and web app steps:

```yaml
steps:
  - command: game
  - expect:
      game: snake                  # the reply carries the game "snake"
  - play:
    url_contains: "snake"
  - command: score 120            # the bot calls setGameScore
  - expect_game_score:
    min_score: 100
  - open_app: arcade
    start_param: ref42
    url_contains: "tgWebAppStartParam=ref42"
```

## Matchers

Used by `expect` and `expect_edit`. A matcher is either a **string**
(shorthand for `equals`) or a **mapping** of clauses. When multiple clauses are
given, **all** must pass.

| Clause | Type | Passes when… |
|--------|------|--------------|
| `equals` | string | Text equals exactly. |
| `contains` | string | Text contains the substring. |
| `icontains` | string | Case-insensitive `contains`. |
| `not_contains` | string | Text does **not** contain the substring. |
| `regex` | string | `re.search` finds the pattern. |
| `iregex` | string | Case-insensitive `regex`. |
| `buttons` | list | All listed buttons are present (order-free): labels, or `{text, data, data_regex}` to check callback data. |
| `buttons_exact` | list | The whole keyboard equals this list (set + order). |
| `has_buttons` | bool | The message has (or has no) keyboard. |
| `game` | string | The message carries a game with this short name. |

```yaml
# string shorthand
- expect: "pong"

# equivalent
- expect:
    equals: "pong"

# combined clauses
- expect:
    icontains: "order #"
    regex: "#\\d+"
    has_buttons: true
```

Text is taken from the message text or, for media, its caption. Button labels
are flattened across all keyboard rows.

## Validation

The parser rejects malformed scenarios up front (raising `ScenarioError`,
CLI exit code 2): a step with zero or multiple action keys, unknown keys, a
missing `steps` list, or invalid YAML. This catches typos before any network
call.
