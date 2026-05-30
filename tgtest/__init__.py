"""tgtest - end-to-end testing platform for Telegram bots.

Acts as a real Telegram *user* (via Telethon/MTProto) to talk to your bots and
assert on their replies. Tests can be written either as declarative YAML
scenarios or as Python/pytest functions using the same client helpers.
"""

from .config import Settings
from .logger import configure_logger
from .client import BotTester, ReplyMatchError
from .scenario import Scenario, load_scenario, load_scenarios
from .engine import run_scenario
from .exceptions import TgTestError, StepError, ScenarioError

__all__ = [
    "Settings",
    "configure_logger",
    "BotTester",
    "ReplyMatchError",
    "Scenario",
    "load_scenario",
    "load_scenarios",
    "run_scenario",
    "TgTestError",
    "StepError",
    "ScenarioError",
]
