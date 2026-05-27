"""Unit tests for the demo bot's pure logic — no Telegram, no aiogram needed."""
from examples.bot import text


def test_reply_for_ping_is_case_insensitive():
    assert text.reply_for("ping") == "pong"
    assert text.reply_for("  PING ") == "pong"


def test_reply_for_echoes_other_text():
    assert text.reply_for("hello") == "You said: hello"


def test_main_menu_shape():
    assert text.main_menu() == [("Settings", "settings"), ("Help", "help")]
