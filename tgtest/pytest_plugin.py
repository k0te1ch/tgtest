"""pytest fixtures for writing Telegram bot E2E tests in Python.

Enable by adding to your conftest.py:

    pytest_plugins = ["tgtest.pytest_plugin"]

Then write async tests:

    import pytest

    @pytest.mark.asyncio
    async def test_start(tester):
        async with tester.conversation("@my_bot") as chat:
            await chat.send("/start")
            await chat.expect(contains="Welcome")

A `run_yaml` fixture is also provided to drive YAML scenarios from pytest:

    @pytest.mark.asyncio
    async def test_scenarios(run_yaml):
        await run_yaml("scenarios/start.yaml")
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from .config import Settings
from .client import BotTester
from .scenario import load_scenarios
from .engine import run_scenario


@pytest.fixture(scope="session")
def tg_config() -> Settings:
    """Load tgtest config once per test session."""
    return Settings.load()


@pytest_asyncio.fixture
async def tester(tg_config):
    """A connected BotTester. One connection per test for clean isolation."""
    async with BotTester.create(tg_config) as bt:
        yield bt


@pytest_asyncio.fixture
async def run_yaml(tester):
    """Return an async callable that runs one or more YAML scenario paths."""
    async def _run(*paths: str):
        for sc in load_scenarios(list(paths)):
            await run_scenario(tester, sc)
    return _run
