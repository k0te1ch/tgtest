"""YAML steps for games and Mini Apps, driven against a fake chat."""

import pytest

from tgtest import engine
from tgtest.apps import GameScore
from tgtest.engine import _Steps
from tgtest.scenario import load_scenario, _parse_step


class FakeChat:
    """Records calls and returns canned URLs / scores."""

    def __init__(self, url="https://app.example/?start=ref42", scores=()):
        self.url = url
        self.scores = list(scores)
        self.calls = []

    async def play(self, timeout=None):
        self.calls.append(("play", timeout))
        return self.url

    async def high_scores(self, timeout=None):
        self.calls.append(("high_scores", timeout))
        return self.scores

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


async def test_high_scores_step_checks_min_entries():
    chat = FakeChat(scores=[GameScore(1, 10, "Ann", 900)])

    await run(chat, {"high_scores": None, "min_entries": 1})
    with pytest.raises(AssertionError, match="at least 2 high score entries, got 1"):
        await run(chat, {"high_scores": None, "min_entries": 2})


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
  - high_scores:
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
        "high_scores",
        "open_menu_app",
        "open_app",
    ]
    assert scenario.steps[1].value == {"game": "snake"}
