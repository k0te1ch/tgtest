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
from contextlib import asynccontextmanager

from telethon import TelegramClient
from telethon.errors import TimeoutError as TelethonTimeout

from .config import Settings
from .matchers import Matcher, button_texts
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


def build_client(config: Settings) -> TelegramClient:
    """Create a (not-yet-connected) TelegramClient, applying any proxy config.

    Shared by BotTester (test runs) and login.py (first-time auth) so both honor
    TG_PROXY identically.
    """
    proxy = parse_proxy(config.proxy)
    return TelegramClient(
        config.session, config.api_id, config.api_hash, **_proxy_kwargs(proxy)
    )


class _Chat:
    """A live conversation with one bot. Tracks the 'current' message so that
    `click`/`expect_buttons`/`expect_edit` operate on the most recent reply."""

    def __init__(self, conv, bot, default_timeout: float):
        self._conv = conv
        self._bot = bot
        self._default_timeout = default_timeout
        self.last = None  # most recent Message we received

    # --- sending --------------------------------------------------------
    async def send(self, text: str):
        """Send a plain text message to the bot."""
        return await self._conv.send_message(text)

    async def command(self, cmd: str):
        """Send a bot command, prepending '/' if the caller omitted it."""
        if not cmd.startswith("/"):
            cmd = "/" + cmd
        return await self._conv.send_message(cmd)

    # --- receiving ------------------------------------------------------
    async def get_reply(self, timeout: float | None = None):
        """Wait for and return the next reply message from the bot."""
        try:
            self.last = await self._conv.get_response(
                timeout=timeout if timeout is not None else self._default_timeout
            )
        except (asyncio.TimeoutError, TelethonTimeout):
            wait = timeout or self._default_timeout
            raise AssertionError(
                f"timed out after {wait}s waiting for a reply"
            ) from None
        return self.last

    async def expect(self, timeout: float | None = None, **spec):
        """Wait for the next reply and assert it matches the given clauses.

        Clauses are the same keys as a YAML `expect` block (equals, contains,
        regex, buttons, ...). Returns the matched Message.
        """
        message = await self.get_reply(timeout=timeout)
        self._assert(Matcher.from_spec(spec), message)
        return message

    async def expect_edit(self, timeout: float | None = None, **spec):
        """Wait for the *current* message to be edited and assert on it.

        Bots commonly edit a message in place after an inline-button click.
        """
        if self.last is None:
            raise AssertionError("expect_edit called before any reply was received")
        try:
            self.last = await self._conv.get_edit(
                self.last,
                timeout=timeout if timeout is not None else self._default_timeout,
            )
        except (asyncio.TimeoutError, TelethonTimeout):
            wait = timeout or self._default_timeout
            raise AssertionError(
                f"timed out after {wait}s waiting for an edit"
            ) from None
        self._assert(Matcher.from_spec(spec), self.last)
        return self.last

    async def expect_no_reply(self, within: float = 2.0):
        """Assert the bot sends nothing within `within` seconds."""
        try:
            msg = await self._conv.get_response(timeout=within)
        except (asyncio.TimeoutError, TelethonTimeout):
            return  # success: nothing arrived
        raise AssertionError(
            f"expected no reply within {within}s but got: {msg.text!r}"
        )

    def expect_buttons(self, *labels: str, exact: bool = False):
        """Assert the current message exposes the given inline/reply buttons."""
        if self.last is None:
            raise AssertionError("expect_buttons called before any reply was received")
        actual = button_texts(self.last)
        if exact:
            if actual != list(labels):
                raise AssertionError(
                    f"buttons differ\n  expected: {list(labels)}\n  actual:   {actual}"
                )
        else:
            missing = [b for b in labels if b not in actual]
            if missing:
                raise AssertionError(
                    f"missing buttons {missing}\n  actual buttons: {actual}"
                )

    # --- interacting ----------------------------------------------------
    async def click(self, text: str | None = None, *, index: int | None = None,
                     data: str | None = None):
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

    # --- internal -------------------------------------------------------
    def _assert(self, matcher: Matcher, message):
        reason = matcher.check(message)
        if reason is not None:
            raise AssertionError(f"{matcher.describe()} failed:\n  {reason}")


class BotTester:
    """Owns the Telethon client connection. Hands out per-bot `_Chat` objects."""

    def __init__(self, client: TelegramClient, config: Settings):
        self._client = client
        self._config = config

    @classmethod
    @asynccontextmanager
    async def create(cls, config: Settings):
        """Connect (using an existing session) and yield a ready BotTester.

        The session must already be authorized; run `python login.py` once to
        create it. We deliberately do NOT prompt for a login code here so that
        test runs never block on interactive input.
        """
        client = build_client(config)
        await client.connect()
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
            yield _Chat(conv, entity, conv_timeout)
