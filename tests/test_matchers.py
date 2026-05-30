"""Unit tests for the matcher logic (no network, safe for CI)."""

from tgtest.matchers import Matcher, button_texts


class _Btn:
    def __init__(self, text):
        self.text = text


class _Msg:
    def __init__(self, text="", buttons=None):
        self.text = text
        self.buttons = buttons


def test_equals_and_contains():
    msg = _Msg("Welcome to the bot")
    assert Matcher.from_spec({"equals": "Welcome to the bot"}).check(msg) is None
    assert Matcher.from_spec({"contains": "Welcome"}).check(msg) is None
    assert Matcher.from_spec({"contains": "Nope"}).check(msg) is not None


def test_string_shorthand_is_equals():
    msg = _Msg("hi")
    assert Matcher.from_spec("hi").check(msg) is None
    assert Matcher.from_spec("bye").check(msg) is not None


def test_case_insensitive_and_regex():
    msg = _Msg("Settings Menu")
    assert Matcher.from_spec({"icontains": "settings"}).check(msg) is None
    assert Matcher.from_spec({"regex": r"^Settings"}).check(msg) is None
    assert Matcher.from_spec({"iregex": r"^settings"}).check(msg) is None
    assert Matcher.from_spec({"not_contains": "Error"}).check(msg) is None


def test_buttons():
    msg = _Msg("menu", [[_Btn("Settings"), _Btn("Help")]])
    assert button_texts(msg) == ["Settings", "Help"]
    assert Matcher.from_spec({"buttons": ["Settings"]}).check(msg) is None
    assert Matcher.from_spec({"buttons": ["Missing"]}).check(msg) is not None
    assert Matcher.from_spec({"buttons_exact": ["Settings", "Help"]}).check(msg) is None
    assert Matcher.from_spec({"buttons_exact": ["Help", "Settings"]}).check(msg)
    assert Matcher.from_spec({"has_buttons": True}).check(msg) is None
    assert Matcher.from_spec({"has_buttons": False}).check(msg) is not None


def test_multiple_clauses_must_all_pass():
    msg = _Msg("Welcome", [[_Btn("Go")]])
    ok = {"contains": "Welcome", "buttons": ["Go"]}
    bad = {"contains": "Welcome", "buttons": ["No"]}
    assert Matcher.from_spec(ok).check(msg) is None
    assert Matcher.from_spec(bad).check(msg) is not None


def test_unknown_key_raises():
    import pytest

    with pytest.raises(ValueError):
        Matcher.from_spec({"bogus": 1})
