"""Unit tests for Settings loading (no network, safe for CI)."""

import pytest

from tgtest.config import Settings


def test_loads_from_env(monkeypatch):
    monkeypatch.setenv("TG_API_ID", "111")
    monkeypatch.setenv("TG_API_HASH", "abc")
    monkeypatch.setenv("TG_DEFAULT_BOT", "@bot")
    # _env_file=None so we don't pick up a developer's local .env during tests.
    s = Settings(_env_file=None)
    assert s.api_id == 111
    assert s.api_hash == "abc"
    assert s.default_bot == "@bot"
    assert s.timeout == 15.0  # default
    assert s.session == "tgtest.session"  # default


def test_missing_credentials_raises_friendly_error(monkeypatch):
    monkeypatch.delenv("TG_API_ID", raising=False)
    monkeypatch.delenv("TG_API_HASH", raising=False)
    with pytest.raises(RuntimeError, match="TG_API_ID"):
        Settings.load(env_file="does-not-exist.env")
