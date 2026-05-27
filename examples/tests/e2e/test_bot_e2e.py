"""Live E2E tests for the demo bot, driven by tgtest.

Run with:  python -m pytest examples/tests/e2e -m e2e
(needs TEST_BOT_TOKEN + TG_* creds + an authorized session — see conftest).
"""
import pytest


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
