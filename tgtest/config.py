"""Application settings, loaded from the environment via pydantic-settings.

Mirrors the project template's `Settings(BaseSettings)` pattern. All tgtest
variables share the ``TG_`` prefix (e.g. ``TG_API_ID`` -> ``api_id``), so both
the CLI runner and the pytest plugin get identical, validated config.
"""

from __future__ import annotations

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """tgtest settings loaded from environment / ``.env`` (prefix ``TG_``)."""

    # Telegram user-account credentials (api_id/api_hash from my.telegram.org).
    api_id: int
    api_hash: str
    # Telethon session file; created once by `python login.py`.
    session: str = "tgtest.session"
    # Phone of the test user account, used only for first-time login.
    phone: str | None = None
    # Bot used when a scenario / test does not name one explicitly.
    default_bot: str | None = None
    # Optional proxy URL, e.g. socks5://user:pass@host:1080 or mtproxy://SECRET@host:443.
    proxy: str | None = None
    # Default per-step reply timeout, in seconds.
    timeout: float = 15.0
    # Logging.
    app_name: str = "tgtest"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="TG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def load(cls, env_file: str | None = None) -> "Settings":
        """Load settings, raising a friendly error if credentials are missing."""
        try:
            return cls(_env_file=env_file) if env_file else cls()
        except ValidationError as exc:
            raise RuntimeError(
                "Invalid tgtest config (see .env.example). "
                "TG_API_ID and TG_API_HASH are required; get them from "
                f"https://my.telegram.org.\n{exc}"
            ) from exc
