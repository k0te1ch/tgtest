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
APP_PROMPT = "Open the demo Mini App:"
APP_BUTTON = "Open app"

# Placeholder game short name: create the game with /newgame in @BotFather and
# set GAME_SHORT_NAME to its short name.
GAME_SHORT_NAME = "demo_game"
GAME_URL = "https://example.com/game"
WEB_APP_URL = "https://example.com/app"
NO_GAME = "Send /game first."
SCORE_USAGE = "Usage: /score [N] with N a non-negative integer."
SCORE_UNCHANGED = "Score unchanged."


def main_menu() -> list[tuple[str, str]]:
    """Inline menu as (label, callback_data) pairs — pure data, easy to test."""
    return [("Settings", "settings"), ("Help", "help")]


def game_link(base_url: str, user_id: int) -> str:
    """URL handed out when a user presses Play: the game page plus who plays."""
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}user={user_id}"


def parse_score(args: str | None) -> int | None:
    """`/score 120` -> 120; a bare `/score` -> None, meaning "current + 1".

    Raises ValueError for anything that is not a non-negative integer.
    """
    if args is None or not args.strip():
        return None
    value = int(args.strip())
    if value < 0:
        raise ValueError(f"negative score: {value}")
    return value


def reply_for(message_text: str) -> str:
    """Reply to free-form text: 'ping' -> 'pong', otherwise echo it back."""
    if message_text.strip().lower() == "ping":
        return "pong"
    return f"You said: {message_text}"
