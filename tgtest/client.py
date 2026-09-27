"""BotTester - the user-facing client for talking to a bot and asserting replies.

Wraps Telethon's `client.conversation()` context, which gives ordered,
timeout-aware access to a bot's replies (including edits and button clicks).
This is the single object both the YAML engine and Python/pytest tests drive.

Typical Python usage:

    async with BotTester.create(config) as tester:
        async with tester.conversation("@my_bot") as chat:
            await chat.send("/start")
            await chat.expect(contains="Welcome", buttons=["Settings"])
            await chat.click("Settings")
            await chat.expect_edit(contains="Settings menu")
"""

from __future__ import annotations

import asyncio
import sqlite3
from contextlib import asynccontextmanager

from telethon import TelegramClient
from telethon.errors import TimeoutError as TelethonTimeout
from telethon.sessions import StringSession

from .apps import AppsMixin
from .config import Settings
from .exceptions import ConnectError, SessionLockedError
from .matchers import (
    Matcher,
    button_texts,
    describe_keyboard,
    game_short_name,
    keyboard,
    missing_buttons,
)
from .proxy import ProxyConfig, parse_proxy

# Re-export so tests can `from tgtest import ReplyMatchError`.
ReplyMatchError = AssertionError


def _proxy_kwargs(proxy: ProxyConfig | None) -> dict:
    """Translate a ProxyConfig into TelegramClient keyword arguments."""
    if proxy is None:
        return {}
    if proxy.kind == "mtproxy":
        # MTProxy needs a dedicated connection class; proxy is (host, port, secret).
        from telethon import connection

        return {
            "connection": connection.ConnectionTcpMTProxyRandomizedIntermediate,
            "proxy": (proxy.host, proxy.port, proxy.secret),
        }
    # python-socks tuple: (kind, host, port, rdns, username, password).
    return {
        "proxy": (
            proxy.kind,
            proxy.host,
            proxy.port,
            proxy.rdns,
            proxy.username,
            proxy.password,
        )
    }


_LOCKED_HINT = (
    "Session {session!r} is locked: another client already uses this file. "
    "Reuse the connected client (`tester.client`) instead of opening a second "
    "one, or set TG_SESSION_STRING (`python login.py --string`), which has no "
    "file to lock."
)


def _lang_kwargs(config: Settings) -> dict:
    if not config.lang_code:
        return {}
    return {
        "lang_code": config.lang_code,
        "system_lang_code": config.system_lang_code or config.lang_code,
    }


def build_client(config: Settings) -> TelegramClient:
    """Create a (not-yet-connected) TelegramClient, applying any proxy config.

    Shared by BotTester (test runs) and login.py (first-time auth) so both honor
    TG_PROXY, TG_LANG_CODE and TG_SESSION_STRING identically.
    """
    proxy = parse_proxy(config.proxy)
    session = (
        StringSession(config.session_string)
        if config.session_string
        else config.session
    )
    try:
        return TelegramClient(
            session,
            config.api_id,
            config.api_hash,
            **_proxy_kwargs(proxy),
            **_lang_kwargs(config),
        )
    except sqlite3.OperationalError as exc:
        if "locked" not in str(exc):
            raise
        raise SessionLockedError(_LOCKED_HINT.format(session=config.session)) from exc


async def connect(client: TelegramClient, config: Settings) -> None:
    """Connect within TG_CONNECT_TIMEOUT, explaining what to check on failure."""
    try:
        await asyncio.wait_for(client.connect(), timeout=config.connect_timeout)
    except sqlite3.OperationalError as exc:
        if "locked" not in str(exc):
            raise
        raise SessionLockedError(_LOCKED_HINT.format(session=config.session)) from exc
    except (asyncio.TimeoutError, OSError) as exc:
        if config.proxy:
            hint = f"Check that the proxy in TG_PROXY ({config.proxy}) is reachable."
        else:
            hint = (
                "Telegram may be blocked on this network: set TG_PROXY "
                "(socks5://host:port or mtproxy://SECRET@host:port)."
            )
        raise ConnectError(
            f"could not connect to Telegram within {config.connect_timeout}s "
            f"({type(exc).__name__}). {hint}"
        ) from exc


def _snapshot(message) -> tuple:
    """What an edit can change: edit date, text and keyboard."""
    text = getattr(message, "text", None) or getattr(message, "message", None)
    return (getattr(message, "edit_date", None), text, tuple(keyboard(message)))


class _Chat(AppsMixin):
    """A live conversation with one bot. Tracks the 'current' message so that
    `click`/`expect_buttons`/`expect_edit` operate on the most recent reply,
    and the last game message for `play`/`expect_game_score`."""

    def __init__(
        self,
        conv,
        bot,
        default_timeout: float,
        *,
        client=None,
        poll_interval: float = 0.5,
    ):
        self._conv = conv
        self._bot = bot
        self._default_timeout = default_timeout
        self._client = client if client is not None else getattr(conv, "_client", None)
        self._poll_interval = poll_interval
        self.last = None  # most recent Message we received
        self.last_game = None  # most recent Message carrying a game
        self._score_seen = 0  # id of the newest game score message consumed

    async def send(self, text: str):
        """Send a plain text message to the bot."""
        return await self._conv.send_message(text)

    async def send_file(self, file, caption: str | None = None, **kwargs):
        """Send a file (path, bytes or file-like) to the bot.

        Extra keyword arguments go to Telethon's `send_file`, e.g.
        `force_document=True` or `voice_note=True`.
        """
        return await self._conv.send_file(file, caption=caption, **kwargs)

    async def command(self, cmd: str):
        """Send a bot command, prepending '/' if the caller omitted it."""
        if not cmd.startswith("/"):
            cmd = "/" + cmd
        return await self._conv.send_message(cmd)

    async def get_reply(self, timeout: float | None = None):
        """Wait for and return the next reply message from the bot."""
        try:
            message = await self._conv.get_response(
                timeout=timeout if timeout is not None else self._default_timeout
            )
        except (asyncio.TimeoutError, TelethonTimeout):
            wait = timeout or self._default_timeout
            raise AssertionError(
                f"timed out after {wait}s waiting for a reply"
            ) from None
        self._remember(message)
        return message

    def _remember(self, message) -> None:
        self.last = message
        if game_short_name(message) is not None:
            self.last_game = message

    async def expect(self, timeout: float | None = None, **spec):
        """Wait for the next reply and assert it matches the given clauses.

        Clauses are the same keys as a YAML `expect` block (equals, contains,
        regex, buttons, ...). Returns the matched Message.
        """
        message = await self.get_reply(timeout=timeout)
        self._assert(Matcher.from_spec(spec), message)
        return message

    async def expect_edit(self, timeout: float | None = None, **spec):
        """Wait until the *current* message is edited into one matching `spec`.

        Bots commonly edit a message in place after an inline-button click,
        sometimes several times (progress, then result). The message is
        re-read from Telegram, so an edit that landed before this call counts
        too: the comparison is against the message as it was received.
        """
        if self.last is None:
            raise AssertionError("expect_edit called before any reply was received")
        before = _snapshot(self.last)
        matcher = Matcher.from_spec(spec)

        def accept(message) -> str | None:
            if _snapshot(message) == before:
                return "the message was not edited"
            return matcher.check(message)

        return await self._poll("an edit", accept, timeout)

    async def wait_until(self, timeout: float | None = None, **spec):
        """Wait until the current message matches `spec`, edited or not.

        For results that arrive later as edits, e.g. a publish status.
        """
        if self.last is None:
            raise AssertionError("wait_until called before any reply was received")
        matcher = Matcher.from_spec(spec)
        return await self._poll(matcher.describe(), matcher.check, timeout)

    async def _poll(self, what: str, accept, timeout: float | None):
        """Re-read the current message until `accept` returns None (no reason)."""
        wait = timeout if timeout is not None else self._default_timeout
        loop = asyncio.get_running_loop()
        deadline = loop.time() + wait
        while True:
            message = await self._reread()
            reason = accept(message)
            if reason is None:
                self._remember(message)
                return message
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise AssertionError(
                    f"timed out after {wait}s waiting for {what}\n  {reason}"
                )
            await asyncio.sleep(min(self._poll_interval, remaining))

    async def _reread(self):
        fresh = await self._client.get_messages(self._bot, ids=self.last.id)
        return fresh if fresh is not None else self.last

    async def expect_no_reply(self, within: float = 2.0):
        """Assert the bot sends nothing within `within` seconds."""
        try:
            msg = await self._conv.get_response(timeout=within)
        except (asyncio.TimeoutError, TelethonTimeout):
            return  # success: nothing arrived
        raise AssertionError(
            f"expected no reply within {within}s but got: {msg.text!r}"
        )

    def expect_buttons(self, *labels, exact: bool = False):
        """Assert the current message exposes the given inline/reply buttons.

        Each entry is a label or a mapping with `text`, `data` and/or
        `data_regex` to check callback data too. `exact` compares labels.
        """
        if self.last is None:
            raise AssertionError("expect_buttons called before any reply was received")
        if exact:
            actual = button_texts(self.last)
            expected = [b if isinstance(b, str) else b.get("text") for b in labels]
            if actual != expected:
                raise AssertionError(
                    f"buttons differ\n  expected: {expected}\n  actual:   {actual}"
                )
            return
        missing = missing_buttons(list(labels), self.last)
        if missing:
            raise AssertionError(
                f"missing buttons {missing}\n"
                f"  actual buttons: {describe_keyboard(self.last)}"
            )

    async def click(
        self,
        text: str | None = None,
        *,
        index: int | None = None,
        data: str | None = None,
    ):
        """Click an inline button on the current message.

        Identify the button by visible `text`, by 0-based `index`, or by raw
        callback `data`.
        """
        if self.last is None:
            raise AssertionError("click called before any reply was received")
        if text is not None:
            return await self.last.click(text=text)
        if data is not None:
            payload = data.encode() if isinstance(data, str) else data
            return await self.last.click(data=payload)
        if index is not None:
            return await self.last.click(index)
        raise ValueError("click requires one of: text, index, data")

    def _assert(self, matcher: Matcher, message):
        reason = matcher.check(message)
        if reason is not None:
            raise AssertionError(f"{matcher.describe()} failed:\n  {reason}")


class BotTester:
    """Owns the Telethon client connection. Hands out per-bot `_Chat` objects."""

    def __init__(self, client: TelegramClient, config: Settings):
        self._client = client
        self._config = config

    @property
    def client(self) -> TelegramClient:
        """The connected Telethon client, for steps tgtest has no helper for.

        Use it instead of opening a second client on the same session file.
        """
        return self._client

    @classmethod
    @asynccontextmanager
    async def create(cls, config: Settings):
        """Connect (using an existing session) and yield a ready BotTester.

        The session must already be authorized; run `python login.py` once to
        create it. We deliberately do NOT prompt for a login code here so that
        test runs never block on interactive input.
        """
        client = build_client(config)
        await connect(client, config)
        if not await client.is_user_authorized():
            await client.disconnect()
            raise RuntimeError(
                f"Session {config.session!r} is not authorized. "
                "Run `python login.py` once to log in."
            )
        try:
            yield cls(client, config)
        finally:
            await client.disconnect()

    @asynccontextmanager
    async def conversation(self, bot: str | None = None, timeout: float | None = None):
        """Open a conversation with `bot` (defaults to TG_DEFAULT_BOT)."""
        target = bot or self._config.default_bot
        if not target:
            raise ValueError("no bot specified and TG_DEFAULT_BOT is not set")
        entity = await self._client.get_entity(target)
        conv_timeout = timeout if timeout is not None else self._config.timeout
        async with self._client.conversation(
            entity, timeout=conv_timeout, total_timeout=None
        ) as conv:
            yield _Chat(
                conv,
                entity,
                conv_timeout,
                client=self._client,
                poll_interval=self._config.poll_interval,
            )
