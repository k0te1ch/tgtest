"""Unit tests for the demo bot's pure logic — no Telegram, no aiogram needed."""

import pytest

from examples.bot import text


def test_reply_for_ping_is_case_insensitive():
    assert text.reply_for("ping") == "pong"
    assert text.reply_for("  PING ") == "pong"


def test_reply_for_echoes_other_text():
    assert text.reply_for("hello") == "You said: hello"


def test_main_menu_shape():
    assert text.main_menu() == [("Settings", "settings"), ("Help", "help")]


def test_game_link_adds_the_player():
    assert (
        text.game_link("https://g.example/play", 7) == "https://g.example/play?user=7"
    )
    assert text.game_link("https://g.example/?lvl=2", 7) == (
        "https://g.example/?lvl=2&user=7"
    )


def test_parse_score():
    assert text.parse_score(" 120 ") == 120
    assert text.parse_score(None) is None
    assert text.parse_score("") is None
    for bad in ("abc", "-5", "1.5"):
        with pytest.raises(ValueError):
            text.parse_score(bad)
