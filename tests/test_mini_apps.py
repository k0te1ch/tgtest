"""Mini App helpers and tgWebAppData parsing against a fake client."""

import json
from dataclasses import dataclass
from urllib.parse import urlencode

import pytest
from telethon.errors import BadRequestError
from telethon.tl import functions, types
from telethon.tl.types.users import UserFull

from tgtest import parse_web_app_data
from tgtest.client import _Chat


@dataclass
class Message:
    reply_markup: object = None
    text: str = ""


def inline(*buttons) -> Message:
    return Message(types.ReplyInlineMarkup([types.KeyboardButtonRow(list(buttons))]))


class FakeClient:
    """Answers by request type; an exception instance is raised instead."""

    def __init__(self, **results):
        self.results = results
        self.requests = []

    async def __call__(self, request):
        self.requests.append(request)
        result = self.results[type(request).__name__]
        if isinstance(result, Exception):
            raise result
        return result

    async def get_input_entity(self, peer):
        return types.InputPeerUser(5, 6)


def chat_with(message, **results) -> _Chat:
    chat = _Chat(None, "bot", 0.2, client=FakeClient(**results))
    chat.last = message
    return chat


def web_view(url="https://app.example/#tgWebAppData=x"):
    return types.WebViewResultUrl(url=url, query_id=1)


async def test_inline_web_app_button_uses_request_web_view():
    chat = chat_with(
        inline(types.KeyboardButtonWebView("Open", "https://app.example")),
        RequestWebViewRequest=web_view(),
    )

    assert await chat.open_web_app("Open") == "https://app.example/#tgWebAppData=x"
    [request] = chat._client.requests
    assert (request.peer, request.bot, request.url) == (
        "bot",
        "bot",
        "https://app.example",
    )
    assert not request.from_bot_menu


async def test_reply_web_app_button_uses_simple_web_view():
    markup = types.ReplyKeyboardMarkup(
        [
            types.KeyboardButtonRow(
                [types.KeyboardButtonSimpleWebView("Shop", "https://shop.example")]
            )
        ]
    )
    chat = chat_with(Message(markup), RequestSimpleWebViewRequest=web_view("u"))

    assert await chat.open_web_app("Shop") == "u"
    [request] = chat._client.requests
    assert isinstance(request, functions.messages.RequestSimpleWebViewRequest)
    assert request.url == "https://shop.example"


async def test_plain_button_is_not_a_web_app():
    chat = chat_with(
        inline(
            types.KeyboardButtonCallback("Open", b"open"),
            types.KeyboardButtonWebView("App", "https://app.example"),
        )
    )

    with pytest.raises(
        AssertionError,
        match=r"(?s)no web_app button 'Open' \(it is KeyboardButtonCallback\)"
        r".*\['App'\]",
    ):
        await chat.open_web_app("Open")


async def test_missing_web_app_button():
    chat = chat_with(inline())

    with pytest.raises(AssertionError, match="no such button"):
        await chat.open_web_app("Open")


async def test_open_web_app_before_any_reply():
    with pytest.raises(AssertionError, match="before any reply"):
        await chat_with(None).open_web_app("Open")


def bot_info(menu_button) -> UserFull:
    full = types.UserFull(
        id=5,
        settings=types.PeerSettings(),
        notify_settings=types.PeerNotifySettings(),
        common_chats_count=0,
        bot_info=types.BotInfo(menu_button=menu_button),
    )
    return UserFull(full_user=full, chats=[], users=[])


async def test_menu_app_opens_the_menu_button_url():
    chat = chat_with(
        None,
        GetFullUserRequest=bot_info(types.BotMenuButton("Play", "https://menu.x")),
        RequestWebViewRequest=web_view("menu-url"),
    )

    assert await chat.open_menu_app() == "menu-url"
    _, request = chat._client.requests
    assert request.from_bot_menu is True
    assert request.url == "https://menu.x"


async def test_menu_without_mini_app():
    chat = chat_with(None, GetFullUserRequest=bot_info(types.BotMenuButtonCommands()))

    with pytest.raises(AssertionError, match="BotMenuButtonCommands"):
        await chat.open_menu_app()


async def test_named_app_passes_short_name_and_start_param():
    chat = chat_with(None, RequestAppWebViewRequest=web_view("app-url"))

    assert await chat.open_app("arcade", start_param="ref42") == "app-url"
    [request] = chat._client.requests
    assert request.app == types.InputBotAppShortName(types.InputUser(5, 6), "arcade")
    assert request.start_param == "ref42"


async def test_unknown_named_app_is_an_assertion():
    chat = chat_with(
        None, RequestAppWebViewRequest=BadRequestError(None, "BOT_APP_INVALID")
    )

    with pytest.raises(AssertionError, match="refused.*'nope'"):
        await chat.open_app("nope")


def mini_app_url(**data) -> str:
    fragment = urlencode({"tgWebAppData": urlencode(data), "tgWebAppVersion": "8.0"})
    return f"https://app.example/index.html#{fragment}"


def test_parse_web_app_data():
    url = mini_app_url(
        query_id="AAHdF6IQ",
        user=json.dumps({"id": 10, "first_name": "Ann"}),
        auth_date="1700000000",
        start_param="ref42",
        hash="abc",
    )

    data = parse_web_app_data(url)

    assert data.user == {"id": 10, "first_name": "Ann"}
    assert data.start_param == "ref42"
    assert data.auth_date == 1700000000
    assert data.query_id == "AAHdF6IQ"
    assert data.raw["hash"] == "abc"


def test_parse_web_app_data_with_missing_fields():
    data = parse_web_app_data(mini_app_url(auth_date="1"))

    assert (data.user, data.start_param, data.query_id) == (None, None, None)


def test_url_without_web_app_data():
    with pytest.raises(AssertionError, match="no tgWebAppData"):
        parse_web_app_data("https://game.example/play?u=1")
