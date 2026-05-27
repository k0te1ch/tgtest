"""Example pytest-style E2E tests. Adjust the bot/assertions for your bot.

Run with:  pytest

These require an authorized session (run `python login.py` once) and a live
bot, so they're marked `live` — skip them in unit CI with `-m "not live"` if
you don't want to hit Telegram.
"""
import pytest

BOT = "@my_bot"  # change to your bot's @username


@pytest.mark.live
async def test_start_shows_welcome(tester):
    async with tester.conversation(BOT) as chat:
        await chat.send("/start")
        await chat.expect(contains="Welcome", buttons=["Settings", "Help"])


@pytest.mark.live
async def test_settings_button_flow(tester):
    async with tester.conversation(BOT) as chat:
        await chat.send("/start")
        await chat.expect(contains="Welcome")
        await chat.click("Settings")
        await chat.expect_edit(icontains="settings")


@pytest.mark.live
async def test_yaml_scenarios(run_yaml):
    # Drive declarative YAML scenarios from within pytest.
    await run_yaml("scenarios/example_start.yaml")
