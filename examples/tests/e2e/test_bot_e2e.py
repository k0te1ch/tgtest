"""Live E2E tests for the demo bot, driven by tgtest.

Run with:  python -m pytest examples/tests/e2e -m e2e
(needs TEST_BOT_TOKEN + TG_* creds + an authorized session — see conftest).
"""

import os
import time

import pytest

from examples.bot import text
from tgtest import parse_web_app_data

GAME = os.environ.get("GAME_SHORT_NAME")
needs_game = pytest.mark.skipif(
    not GAME, reason="create a game with /newgame and set GAME_SHORT_NAME"
)


@pytest.mark.e2e
async def test_start_shows_menu(bot_process, tester):
    async with tester.conversation() as chat:  # uses TG_DEFAULT_BOT
        await chat.send("/start")
        await chat.expect(contains="Welcome", buttons=["Settings", "Help"])


@pytest.mark.e2e
async def test_settings_button_edits_message(bot_process, tester):
    async with tester.conversation() as chat:
        await chat.send("/start")
        await chat.expect(contains="Welcome")
        await chat.click("Settings")
        await chat.expect_edit(icontains="settings")


@pytest.mark.e2e
async def test_ping_pong(bot_process, tester):
    async with tester.conversation() as chat:
        await chat.send("ping")
        await chat.expect(equals="pong")


@pytest.mark.e2e
async def test_yaml_scenarios(bot_process, run_yaml):
    await run_yaml("examples/tests/e2e/scenarios/start.yaml")


@pytest.mark.e2e
@needs_game
async def test_game_play_returns_the_game_url(bot_process, tester):
    async with tester.conversation() as chat:
        await chat.command("game")
        await chat.expect(game=GAME)
        url = await chat.play()
        me = await tester.client.get_me()
        assert url.endswith(f"user={me.id}")

        points = int(time.time()) % 1_000_000  # differs per run: setGameScore
        await chat.command(f"score {points}")  # rejects an unchanged score
        assert await chat.expect_game_score(exact=points) == points


@pytest.mark.e2e
async def test_web_app_button_opens_the_mini_app(bot_process, tester):
    async with tester.conversation() as chat:
        await chat.command("app")
        await chat.expect(contains=text.APP_PROMPT, buttons=[text.APP_BUTTON])
        url = await chat.open_web_app(text.APP_BUTTON)
        data = parse_web_app_data(url)
        me = await tester.client.get_me()
        assert data.user["id"] == me.id


@pytest.mark.e2e
async def test_yaml_mini_app(bot_process, run_yaml):
    await run_yaml("examples/tests/e2e/scenarios/mini_app.yaml")


@pytest.mark.e2e
@pytest.mark.skipif(GAME != "demo_game", reason="game.yaml expects demo_game")
async def test_yaml_game(bot_process, run_yaml):
    await run_yaml("examples/tests/e2e/scenarios/game.yaml")
