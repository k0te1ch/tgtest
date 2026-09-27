"""Bot games and Mini Apps: pressing Play, reading high scores, opening web apps.

`_Chat` inherits these helpers from `AppsMixin`. Each call goes straight to
Telegram through the connected client and returns what the bot or Telegram
answered (a URL or a score table), so tests can assert on it.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from telethon import utils
from telethon.errors import RPCError
from telethon.tl import functions, types


@dataclass(frozen=True)
class GameScore:
    """One row of a game's high score table."""

    position: int
    user_id: int
    name: str
    score: int


def raw_buttons(message) -> list:
    """Every raw Telethon keyboard button of a message, row by row."""
    markup = getattr(message, "reply_markup", None)
    return [
        button for row in getattr(markup, "rows", None) or [] for button in row.buttons
    ]


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
