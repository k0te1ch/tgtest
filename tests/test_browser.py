"""assert_page_loads against a fake Playwright module (no browser)."""

import sys
import types
from dataclasses import dataclass, field

import pytest

from tgtest.browser import assert_page_loads


class FakeError(Exception):
    pass


@dataclass
class Response:
    status: int = 200

    @property
    def ok(self) -> bool:
        return self.status < 400


@dataclass
class Page:
    response: Response | None = None
    page_errors: list = field(default_factory=list)
    fail: bool = False
    handlers: dict = field(default_factory=dict)
    visited: list = field(default_factory=list)

    def on(self, event, handler):
        self.handlers[event] = handler

    async def goto(self, url, wait_until, timeout):
        self.visited.append((url, wait_until, timeout))
        if self.fail:
            raise FakeError("Timeout 1000ms exceeded")
        for error in self.page_errors:
            self.handlers["pageerror"](error)
        return self.response


class Browser:
    def __init__(self, page):
        self.page = page
        self.closed = False

    async def new_page(self):
        return self.page

    async def close(self):
        self.closed = True


def install(monkeypatch, page: Page) -> Browser:
    browser = Browser(page)

    class Chromium:
        async def launch(self):
            return browser

    class Playwright:
        chromium = Chromium()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    module = types.ModuleType("playwright.async_api")
    module.Error = FakeError
    module.async_playwright = Playwright
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.async_api", module)
    return browser


async def test_page_that_loads_passes(monkeypatch):
    page = Page(Response(200))
    browser = install(monkeypatch, page)

    await assert_page_loads("https://game.example", timeout=1)

    assert page.visited == [("https://game.example", "load", 1000)]
    assert browser.closed


async def test_script_error_fails(monkeypatch):
    install(monkeypatch, Page(Response(200), page_errors=["x is not defined"]))

    with pytest.raises(AssertionError, match="1 error.*\n  x is not defined"):
        await assert_page_loads("https://game.example")


async def test_http_error_fails(monkeypatch):
    install(monkeypatch, Page(Response(404)))

    with pytest.raises(AssertionError, match="HTTP 404"):
        await assert_page_loads("https://game.example")


async def test_load_timeout_fails_and_closes_the_browser(monkeypatch):
    browser = install(monkeypatch, Page(fail=True))

    with pytest.raises(AssertionError, match="did not load within 1s"):
        await assert_page_loads("https://game.example", timeout=1)
    assert browser.closed


async def test_missing_extra_says_how_to_install(monkeypatch):
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.async_api", None)

    with pytest.raises(ImportError, match=r"tgtest\[browser\]"):
        await assert_page_loads("https://game.example")
