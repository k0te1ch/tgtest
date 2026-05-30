"""Pure, framework-free bot logic and copy.

Keeping the decision logic and message text here (with no aiogram imports)
means it can be covered by fast unit tests, while ``app.py`` only wires these
into handlers. This is the split that lets unit and E2E tests coexist.
"""

from __future__ import annotations

WELCOME = "Welcome to the demo bot!"
SETTINGS = "Settings menu — nothing to configure yet."
HELP = "Help: send /start, press a button, or say 'ping'."
UNKNOWN = "Unknown command."


def main_menu() -> list[tuple[str, str]]:
    """Inline menu as (label, callback_data) pairs — pure data, easy to test."""
    return [("Settings", "settings"), ("Help", "help")]


def reply_for(message_text: str) -> str:
    """Reply to free-form text: 'ping' -> 'pong', otherwise echo it back."""
    if message_text.strip().lower() == "ping":
        return "pong"
    return f"You said: {message_text}"
