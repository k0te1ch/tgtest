"""YAML steps for games and Mini Apps, driven against a fake chat."""

import pytest

from tgtest import engine
from tgtest.engine import _Steps
from tgtest.scenario import load_scenario, _parse_step


class FakeChat:
    """Records calls and returns canned URLs / scores."""

    def __init__(self, url="https://app.example/?start=ref42", score=120):
        self.url = url
        self.score = score
        self.calls = []

    async def play(self, timeout=None):
        self.calls.append(("play", timeout))
        return self.url

    async def expect_game_score(self, exact=None, min_score=None, timeout=None):
        self.calls.append(("expect_game_score", exact, min_score))
        return self.score

    async def open_web_app(self, text, timeout=None):
        self.calls.append(("open_web_app", text))
        return self.url

    async def open_menu_app(self, timeout=None):
        self.calls.append(("open_menu_app", timeout))
        return self.url

    async def open_app(self, short_name, start_param=None, timeout=None):
        self.calls.append(("open_app", short_name, start_param))
        return self.url


async def run(chat, raw: dict):
    step = _parse_step(raw, 0)
    timeout = float(step.options["timeout"]) if "timeout" in step.options else None
    await getattr(_Steps(chat, step.value, step.options, timeout), step.action)()


async def test_play_step_checks_the_url():
    chat = FakeChat()

    await run(chat, {"play": None, "url_contains": "app.example", "timeout": 3})

    assert chat.calls == [("play", 3.0)]


async def test_url_mismatch_is_reported():
    with pytest.raises(AssertionError, match="does not contain 'game'.*\n  actual"):
        await run(FakeChat(), {"play": None, "url_contains": "game"})
    with pytest.raises(AssertionError, match="does not match"):
        await run(FakeChat(), {"open_menu_app": None, "url_regex": "^http://"})


async def test_open_web_app_step_passes_the_button_text():
    chat = FakeChat()

    await run(chat, {"open_web_app": "Open shop", "url_regex": r"start=ref\d+"})

    assert chat.calls == [("open_web_app", "Open shop")]


async def test_open_app_step_passes_start_param():
    chat = FakeChat()

    await run(chat, {"open_app": "arcade", "start_param": "ref42"})

    assert chat.calls == [("open_app", "arcade", "ref42")]


async def test_expect_game_score_step_passes_exact_and_minimum():
    chat = FakeChat()

    await run(chat, {"expect_game_score": 120})
    await run(chat, {"expect_game_score": None, "min_score": 100})

    assert chat.calls == [
        ("expect_game_score", 120, None),
        ("expect_game_score", None, 100),
    ]


async def test_page_loads_opens_the_url(monkeypatch):
    opened = []

    async def fake_page_loads(url, timeout):
        opened.append((url, timeout))

    monkeypatch.setattr(engine, "assert_page_loads", fake_page_loads)

    await run(FakeChat(url="https://g.example"), {"play": None, "page_loads": True})

    assert opened == [("https://g.example", 30.0)]


def test_scenario_with_game_steps_parses(tmp_path):
    path = tmp_path / "game.yaml"
    path.write_text(
        """
name: Game
steps:
  - command: game
  - expect:
      game: snake
  - play:
    url_contains: "snake"
  - expect_game_score: 120
  - open_menu_app:
  - open_app: arcade
    start_param: ref42
""",
        encoding="utf-8",
    )

    [scenario] = load_scenario(str(path))

    assert [s.action for s in scenario.steps] == [
        "command",
        "expect",
        "play",
        "expect_game_score",
        "open_menu_app",
        "open_app",
    ]
    assert scenario.steps[1].value == {"game": "snake"}
