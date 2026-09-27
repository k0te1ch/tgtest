"""Unit tests for client construction and the chat helpers (no network)."""

import asyncio
import sqlite3

import pytest
from telethon.crypto import AuthKey
from telethon.sessions import StringSession

from tgtest import client as client_module
from tgtest.client import BotTester, _Chat, build_client, connect
from tgtest.config import Settings
from tgtest.engine import _Steps
from tgtest.exceptions import ConnectError, SessionLockedError
from tgtest.scenario import _parse_step


def settings(tmp_path, **overrides) -> Settings:
    values = {"api_id": 1, "api_hash": "hash", "session": str(tmp_path / "t.session")}
    return Settings(_env_file=None, **{**values, **overrides})


def test_language_is_passed_to_telegram(tmp_path):
    client = build_client(settings(tmp_path, lang_code="ru"))

    assert client._init_request.lang_code == "ru"
    assert client._init_request.system_lang_code == "ru"


def test_system_language_can_differ(tmp_path):
    client = build_client(settings(tmp_path, lang_code="ru", system_lang_code="en"))

    assert client._init_request.system_lang_code == "en"


def test_telethon_default_language_without_setting(tmp_path):
    assert build_client(settings(tmp_path))._init_request.lang_code == "en"


def saved_string_session() -> str:
    session = StringSession()
    session.set_dc(2, "149.154.167.51", 443)
    session.auth_key = AuthKey(bytes(256))
    return session.save()


def test_session_string_needs_no_file(tmp_path):
    client = build_client(settings(tmp_path, session_string=saved_string_session()))

    assert isinstance(client.session, StringSession)
    assert not (tmp_path / "t.session").exists()


def test_locked_session_explains_what_to_do(tmp_path, monkeypatch):
    def locked(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(client_module, "TelegramClient", locked)

    with pytest.raises(SessionLockedError, match="tester.client.*TG_SESSION_STRING"):
        build_client(settings(tmp_path))


def test_other_sqlite_errors_are_not_masked(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(client_module, "TelegramClient", broken)

    with pytest.raises(sqlite3.OperationalError, match="disk I/O"):
        build_client(settings(tmp_path))


class HangingClient:
    async def connect(self):
        await asyncio.sleep(10)


async def test_connect_timeout_suggests_a_proxy(tmp_path):
    with pytest.raises(ConnectError, match="within 0.01s.*set TG_PROXY"):
        await connect(HangingClient(), settings(tmp_path, connect_timeout=0.01))


async def test_connect_timeout_points_at_the_configured_proxy(tmp_path):
    config = settings(tmp_path, connect_timeout=0.01, proxy="socks5://10.0.0.1:1080")

    with pytest.raises(ConnectError, match="10.0.0.1:1080.*reachable"):
        await connect(HangingClient(), config)


def test_tester_exposes_its_client(tmp_path):
    client = object()

    assert BotTester(client, settings(tmp_path)).client is client


class FakeConversation:
    def __init__(self):
        self.files = []

    async def send_file(self, file, **kwargs):
        self.files.append((file, kwargs))


async def test_send_file_passes_caption_and_options():
    conv = FakeConversation()

    await _Chat(conv, bot=None, default_timeout=1).send_file(
        "a.mp3", caption="episode", force_document=True
    )

    assert conv.files == [("a.mp3", {"caption": "episode", "force_document": True})]


async def test_yaml_send_file_step():
    conv = FakeConversation()
    step = _parse_step({"send_file": "a.mp3", "caption": "episode"}, 0)

    await getattr(
        _Steps(_Chat(conv, None, 1), step.value, step.options, None), step.action
    )()

    assert conv.files == [("a.mp3", {"caption": "episode", "force_document": False})]
