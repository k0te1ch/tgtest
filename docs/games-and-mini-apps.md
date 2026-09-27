# Games & Mini Apps

Telegram has two ways for a bot to open a web page inside the app, and tgtest
can drive both from the test user's side.

Sources: [`tgtest/apps.py`](../tgtest/apps.py) (games and Mini Apps),
[`tgtest/browser.py`](../tgtest/browser.py) (optional page check),
[`tgtest/matchers.py`](../tgtest/matchers.py) (`game` matcher).

## Games vs Mini Apps

| | Games | Mini Apps (Web Apps) |
|---|---|---|
| Created with | @BotFather `/newgame` (gets a short name) | @BotFather `/newapp` for named apps; any HTTPS URL for buttons |
| Arrives as | a message with a game (`sendGame`) and a **Play** button | a `web_app` button (inline or reply keyboard), the bot's menu button, or a `t.me/<bot>/<app>` link |
| URL comes from | **the bot**: it answers the Play callback with `answerCallbackQuery(url=...)` | **Telegram**: it signs launch data and appends it to the URL fragment as `tgWebAppData` |
| Score table | yes, `setGameScore` / `getGameHighScores` | no |

So for a game tgtest checks that the bot hands out a URL; for a Mini App it
checks that Telegram opens the configured page with the expected launch data.

## Python API

All helpers are methods of the conversation object (`_Chat`) and return plain
values you can assert on. Failures raise `AssertionError` with the reason.

| Method | Returns | What it does |
|--------|---------|--------------|
| `await chat.expect(game="snake")` | `Message` | The next reply must carry the game `snake`. |
| `await chat.play(timeout=None)` | `str` | Presses the game button of the last game message (`GetBotCallbackAnswer` with `game=True`) and returns the bot's URL. |
| `await chat.high_scores(user="me", timeout=None)` | `list[GameScore]` | `GetGameHighScores` for the last game message: rows around `user`. |
| `await chat.open_web_app(text, timeout=None)` | `str` | Opens the `web_app` button `text` of the current message. Inline buttons use `RequestWebView`, reply keyboard buttons `RequestSimpleWebView`. |
| `await chat.open_menu_app(timeout=None)` | `str` | Opens the Mini App behind the bot's menu button (`RequestWebView` with `from_bot_menu`). |
| `await chat.open_app(short_name, start_param=None, timeout=None)` | `str` | Opens the named Mini App `t.me/<bot>/<short_name>` (`RequestAppWebView`). |
| `parse_web_app_data(url)` | `WebAppData` | Parses `tgWebAppData` from a Mini App URL. |
| `await assert_page_loads(url, timeout=30.0)` | `None` | Opens the URL headless; fails on JS errors, HTTP errors, or no `load` in time. |

"The last game message" is the most recent reply that carried a game, even if
text replies came after it. `GameScore` has `position`, `user_id`, `name` and
`score`. `WebAppData` has `user` (dict), `start_param`, `auth_date`,
`query_id` and `raw` (every field as sent, including `hash`).

```python
from tgtest import parse_web_app_data
from tgtest.browser import assert_page_loads


async def test_game(tester):
    async with tester.conversation("@my_bot") as chat:
        await chat.command("game")
        await chat.expect(game="snake")

        url = await chat.play()
        assert url.startswith("https://game.example/")
        await assert_page_loads(url)        # optional, needs the browser extra

        scores = await chat.high_scores()
        assert scores == [] or scores[0].position == 1


async def test_mini_app(tester):
    async with tester.conversation("@my_bot") as chat:
        url = await chat.open_app("arcade", start_param="ref42")
        data = parse_web_app_data(url)
        assert data.start_param == "ref42"
        assert data.user["id"] == (await tester.client.get_me()).id
```

## YAML

| Step | Value | Modifiers |
|------|-------|-----------|
| `expect: {game: <short_name>}` | matcher | any matcher clause |
| `play` | empty | `url_contains`, `url_regex`, `page_loads`, `timeout` |
| `high_scores` | empty | `min_entries`, `timeout` |
| `open_web_app` | button label | `url_contains`, `url_regex`, `page_loads`, `timeout` |
| `open_menu_app` | empty | `url_contains`, `url_regex`, `page_loads`, `timeout` |
| `open_app` | short name | `start_param`, `url_contains`, `url_regex`, `page_loads`, `timeout` |

```yaml
name: Game and Mini App
steps:
  - command: game
  - expect:
      game: snake
  - play:
    url_contains: "snake"
    page_loads: true          # needs tgtest[browser]
  - high_scores:
  - command: start
  - expect:
      buttons: ["Open app"]
  - open_web_app: "Open app"
    url_contains: "tgWebAppData"
  - open_app: arcade
    start_param: ref42
```

## Optional browser check

`assert_page_loads` and the `page_loads: true` modifier use Playwright, which is
not installed by default:

```powershell
pip install "tgtest[browser]"
playwright install chromium
```

Without the extra, the call raises `ImportError` explaining what to install.
The check opens the page in headless Chromium, waits for the `load` event and
fails on uncaught JavaScript errors or an HTTP error status. It does not log
in, click, or run the game; for that, write Playwright code against the URL.

## Limits

- The game URL is whatever the bot returns; tgtest does not validate the
  game's own signature or score reporting. Score changes (`setGameScore`)
  happen on the bot side and show up in `high_scores`.
- Opening a Mini App tells Telegram the user launched it. The bot may receive
  `web_app_data` or send messages as a result, so expect those in the
  conversation if your bot does that.
- `tgWebAppData` is signed with the bot token. tgtest parses it but does not
  verify the `hash`; the Mini App backend should do that.
- The `platform` reported to Telegram is `tdesktop` (`tgtest.apps.PLATFORM`).
- Games must be created with @BotFather `/newgame`, named Mini Apps with
  `/newapp`, and a menu button needs BotFather or `setChatMenuButton`. Without
  them the calls fail with Telegram's error in the message.
