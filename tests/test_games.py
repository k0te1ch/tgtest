"""play and expect_game_score against a fake client (no network)."""

import asyncio
from dataclasses import dataclass

import pytest
from telethon.errors import BotResponseTimeoutError
from telethon.tl import functions, types
from telethon.tl.types.messages import BotCallbackAnswer

from tgtest.client import _Chat


@dataclass
class Message:
    text: str = ""
    media: object = None
    reply_markup: object = None
    buttons: object = None
    id: int = 42


def game_message(short_name="snake", buttons=None) -> Message:
    game = types.Game(1, 2, short_name, "Snake", "Eat apples", types.PhotoEmpty(0))
    if buttons is None:
        buttons = [types.KeyboardButtonGame("Play Snake")]
    markup = types.ReplyInlineMarkup([types.KeyboardButtonRow(buttons)])
    return Message(media=types.MessageMediaGame(game), reply_markup=markup)


class FakeConversation:
    def __init__(self, *replies):
        self.replies = list(replies)

    async def get_response(self, timeout):
        return self.replies.pop(0)


class FakeClient:
    """Answers each request with a canned result (or raises it)."""

    def __init__(self, result=None, delay: float = 0, history=()):
        self.result = result
        self.delay = delay
        self.requests = []
        self.history = list(history)
        self.reads = []

    async def get_messages(self, chat, min_id, limit, reverse):
        self.reads.append(min_id)
        return [m for m in self.history if m.id > min_id][:limit]

    async def __call__(self, request):
        self.requests.append(request)
        await asyncio.sleep(self.delay)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


async def chat_after(*replies, client=None) -> _Chat:
    chat = _Chat(FakeConversation(*replies), "bot", 0.2, client=client or FakeClient())
    for _ in replies:
        await chat.get_reply()
    return chat


async def test_expect_game_remembers_the_game_message():
    chat = await chat_after(game_message())

    assert chat.last_game is chat.last


async def test_later_text_reply_keeps_the_game_message():
    game = game_message()
    chat = await chat_after(game, Message("Good luck!"))

    assert chat.last_game is game
    assert chat.last.text == "Good luck!"


async def test_expect_matches_game_short_name():
    chat = _Chat(FakeConversation(game_message("snake"), Message("text")), "bot", 0.2)

    await chat.expect(game="snake")
    with pytest.raises(AssertionError, match="has no game"):
        await chat.expect(game="snake")


async def test_play_presses_the_game_button_and_returns_the_url():
    client = FakeClient(BotCallbackAnswer(0, url="https://game.example/?u=1"))
    chat = await chat_after(game_message(), client=client)

    assert await chat.play() == "https://game.example/?u=1"
    [request] = client.requests
    assert isinstance(request, functions.messages.GetBotCallbackAnswerRequest)
    assert (request.peer, request.msg_id, request.game) == ("bot", 42, True)


async def test_play_without_url_explains_the_bot_side():
    client = FakeClient(BotCallbackAnswer(0, message="no game today"))
    chat = await chat_after(game_message(), client=client)

    with pytest.raises(AssertionError, match="without a URL.*no game today"):
        await chat.play()


async def test_play_without_game_button():
    chat = await chat_after(
        game_message(buttons=[types.KeyboardButtonUrl("Site", "https://x.y")])
    )

    with pytest.raises(AssertionError, match=r"no game button\n.*'Site'"):
        await chat.play()


async def test_play_before_any_game():
    chat = await chat_after(Message("hi"))

    with pytest.raises(AssertionError, match="play called before any game"):
        await chat.play()


async def test_play_times_out():
    client = FakeClient(BotCallbackAnswer(0, url="u"), delay=1)
    chat = await chat_after(game_message(), client=client)

    with pytest.raises(AssertionError, match="timed out after 0.01s.*game URL"):
        await chat.play(timeout=0.01)


async def test_telegram_error_becomes_an_assertion():
    client = FakeClient(BotResponseTimeoutError(request=None))
    chat = await chat_after(game_message(), client=client)

    with pytest.raises(AssertionError, match="Telegram refused.*game URL"):
        await chat.play()


@dataclass
class ServiceMessage:
    id: int
    action: object


def score(msg_id: int, points: int, game_id: int = 1) -> ServiceMessage:
    return ServiceMessage(msg_id, types.MessageActionGameScore(game_id, points))


async def score_chat(*history) -> _Chat:
    chat = await chat_after(game_message(), client=FakeClient(history=history))
    chat._poll_interval = 0.01
    return chat


async def test_score_message_of_the_last_game_is_returned():
    chat = await score_chat(ServiceMessage(43, None), score(44, 120))

    assert await chat.expect_game_score(exact=120, min_score=100) == 120
    assert chat._client.reads == [42]


async def test_each_score_message_is_consumed_once():
    chat = await score_chat(score(44, 10), score(45, 30))

    assert await chat.expect_game_score() == 10
    assert await chat.expect_game_score() == 30
    assert chat._client.reads == [42, 44]


async def test_scores_of_other_games_are_skipped():
    chat = await score_chat(score(44, 999, game_id=7), score(45, 5))

    assert await chat.expect_game_score() == 5


async def test_wrong_score_is_reported():
    chat = await score_chat(score(44, 80))

    with pytest.raises(AssertionError, match=r"expected: 100\n  actual:   80"):
        await chat.expect_game_score(exact=100)


async def test_score_below_minimum_is_reported():
    chat = await score_chat(score(44, 80))

    with pytest.raises(AssertionError, match="80 is below the minimum 100"):
        await chat.expect_game_score(min_score=100)


async def test_no_score_message_times_out():
    chat = await score_chat(ServiceMessage(43, None))

    with pytest.raises(AssertionError, match="timed out.*score message.*'snake'"):
        await chat.expect_game_score(timeout=0.05)


async def test_score_before_any_game():
    chat = await chat_after(Message("hi"))

    with pytest.raises(AssertionError, match="before any game message"):
        await chat.expect_game_score()
