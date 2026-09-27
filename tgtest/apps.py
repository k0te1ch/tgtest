"""Bot games and Mini Apps: pressing Play, reading high scores, opening web apps.

`_Chat` inherits these helpers from `AppsMixin`. Each call goes straight to
Telegram through the connected client and returns what the bot or Telegram
answered (a URL or a score table), so tests can assert on it.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from urllib.parse import parse_qs, parse_qsl, urlsplit

from telethon import utils
from telethon.errors import RPCError
from telethon.tl import functions, types

# Platform reported to Telegram when opening a Mini App; ends up in the URL.
PLATFORM = "tdesktop"


@dataclass(frozen=True)
class GameScore:
    """One row of a game's high score table."""

    position: int
    user_id: int
    name: str
    score: int


@dataclass(frozen=True)
class WebAppData:
    """The launch data Telegram put into a Mini App URL (`tgWebAppData`).

    `raw` keeps every field as sent, including `hash` and `signature`.
    """

    user: dict | None
    start_param: str | None
    auth_date: int | None
    query_id: str | None
    raw: dict[str, str] = field(default_factory=dict)


def parse_web_app_data(url: str) -> WebAppData:
    """Parse `tgWebAppData` from the fragment of a Mini App URL."""
    fragment = parse_qs(urlsplit(url).fragment)
    if "tgWebAppData" not in fragment:
        raise AssertionError(f"no tgWebAppData in the URL fragment: {url!r}")
    raw = dict(parse_qsl(fragment["tgWebAppData"][0], keep_blank_values=True))
    return WebAppData(
        user=json.loads(raw["user"]) if "user" in raw else None,
        start_param=raw.get("start_param"),
        auth_date=int(raw["auth_date"]) if "auth_date" in raw else None,
        query_id=raw.get("query_id"),
        raw=raw,
    )


def raw_buttons(message) -> list:
    """Every raw Telethon keyboard button of a message, row by row."""
    markup = getattr(message, "reply_markup", None)
    return [
        button for row in getattr(markup, "rows", None) or [] for button in row.buttons
    ]


def _is_web_app(button) -> bool:
    return isinstance(
        button, (types.KeyboardButtonWebView, types.KeyboardButtonSimpleWebView)
    )


class AppsMixin:
    """Games and Mini App helpers for a conversation with one bot."""

    _client: object
    _bot: object
    _default_timeout: float
    last: object | None
    last_game: object | None

    async def play(self, timeout: float | None = None) -> str:
        """Press the game button of the last game message, return the game URL.

        The bot must answer the callback with `answerCallbackQuery(url=...)`.
        """
        message = self._game_message("play")
        buttons = raw_buttons(message)
        if not any(isinstance(b, types.KeyboardButtonGame) for b in buttons):
            labels = [getattr(b, "text", None) for b in buttons]
            raise AssertionError(
                f"game message has no game button\n  buttons: {labels}"
            )
        request = functions.messages.GetBotCallbackAnswerRequest(
            peer=self._bot, msg_id=message.id, game=True
        )
        answer = await self._request(request, timeout, "the game URL")
        if not answer.url:
            raise AssertionError(
                "the bot answered the game button without a URL "
                f"(message={answer.message!r}); it must call "
                "answerCallbackQuery with url="
            )
        return answer.url

    async def high_scores(
        self, user="me", timeout: float | None = None
    ) -> list[GameScore]:
        """High scores of the last game message around `user` (default: us)."""
        message = self._game_message("high_scores")
        request = functions.messages.GetGameHighScoresRequest(
            peer=self._bot, id=message.id, user_id=user
        )
        result = await self._request(request, timeout, "the high scores")
        names = {u.id: utils.get_display_name(u) for u in result.users}
        return [
            GameScore(s.pos, s.user_id, names.get(s.user_id, ""), s.score)
            for s in result.scores
        ]

    async def open_web_app(self, text: str, timeout: float | None = None) -> str:
        """Open the web_app button `text` of the current message, return its URL.

        Works for inline buttons (`KeyboardButtonWebView`) and reply keyboard
        buttons (`KeyboardButtonSimpleWebView`).
        """
        if self.last is None:
            raise AssertionError("open_web_app called before any reply was received")
        button = next((b for b in raw_buttons(self.last) if b.text == text), None)
        if isinstance(button, types.KeyboardButtonWebView):
            request = functions.messages.RequestWebViewRequest(
                peer=self._bot, bot=self._bot, platform=PLATFORM, url=button.url
            )
        elif isinstance(button, types.KeyboardButtonSimpleWebView):
            request = functions.messages.RequestSimpleWebViewRequest(
                bot=self._bot, platform=PLATFORM, url=button.url
            )
        else:
            found = f"it is {type(button).__name__}" if button else "no such button"
            labels = [b.text for b in raw_buttons(self.last) if _is_web_app(b)]
            raise AssertionError(
                f"no web_app button {text!r} ({found})\n  web_app buttons: {labels}"
            )
        result = await self._request(request, timeout, "the Mini App URL")
        return result.url

    async def open_menu_app(self, timeout: float | None = None) -> str:
        """Open the Mini App behind the bot's menu button, return its URL."""
        full = await self._request(
            functions.users.GetFullUserRequest(self._bot), timeout, "the bot info"
        )
        menu = getattr(full.full_user.bot_info, "menu_button", None)
        if not isinstance(menu, types.BotMenuButton):
            raise AssertionError(
                "the bot's menu button does not open a Mini App "
                f"({type(menu).__name__}); set it with BotFather or "
                "setChatMenuButton"
            )
        request = functions.messages.RequestWebViewRequest(
            peer=self._bot,
            bot=self._bot,
            platform=PLATFORM,
            from_bot_menu=True,
            url=menu.url,
        )
        result = await self._request(request, timeout, "the menu Mini App URL")
        return result.url

    async def open_app(
        self,
        short_name: str,
        start_param: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """Open the named Mini App `t.me/<bot>/<short_name>`, return its URL."""
        bot = utils.get_input_user(await self._client.get_input_entity(self._bot))
        request = functions.messages.RequestAppWebViewRequest(
            peer=self._bot,
            app=types.InputBotAppShortName(bot_id=bot, short_name=short_name),
            platform=PLATFORM,
            start_param=start_param,
        )
        result = await self._request(request, timeout, f"the Mini App {short_name!r}")
        return result.url

    def _game_message(self, what: str):
        if self.last_game is None:
            raise AssertionError(f"{what} called before any game message was received")
        return self.last_game

    async def _request(self, request, timeout: float | None, what: str):
        wait = timeout if timeout is not None else self._default_timeout
        try:
            return await asyncio.wait_for(self._client(request), timeout=wait)
        except asyncio.TimeoutError:
            raise AssertionError(
                f"timed out after {wait}s waiting for {what}"
            ) from None
        except RPCError as exc:
            raise AssertionError(
                f"Telegram refused the request for {what}: {exc}"
            ) from exc
