"""Unit tests for YAML scenario parsing (no network, safe for CI)."""
import pytest

from tgtest.scenario import load_scenario, load_scenarios
from tgtest.exceptions import ScenarioError


def _write(tmp_path, text, name="s.yaml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_parses_single_scenario(tmp_path):
    path = _write(tmp_path, """
name: Demo
bot: "@b"
timeout: 5
steps:
  - command: start
  - expect:
      contains: Hi
  - click: "Go"
""")
    [sc] = load_scenario(path)
    assert sc.name == "Demo"
    assert sc.bot == "@b"
    assert sc.timeout == 5.0
    assert [s.action for s in sc.steps] == ["command", "expect", "click"]


def test_multi_document_file(tmp_path):
    path = _write(tmp_path, """
name: One
steps:
  - send: a
---
name: Two
steps:
  - send: b
""")
    scs = load_scenario(path)
    assert [s.name for s in scs] == ["One", "Two"]


def test_load_scenarios_from_dir(tmp_path):
    _write(tmp_path, "name: A\nsteps:\n  - send: x\n", "a.yaml")
    _write(tmp_path, "name: B\nsteps:\n  - send: y\n", "b.yml")
    scs = load_scenarios([str(tmp_path)])
    assert {s.name for s in scs} == {"A", "B"}


def test_step_with_two_actions_errors(tmp_path):
    path = _write(tmp_path, "name: X\nsteps:\n  - send: a\n    expect: b\n")
    with pytest.raises(ScenarioError):
        load_scenario(path)


def test_missing_steps_errors(tmp_path):
    path = _write(tmp_path, "name: X\n")
    with pytest.raises(ScenarioError):
        load_scenario(path)
