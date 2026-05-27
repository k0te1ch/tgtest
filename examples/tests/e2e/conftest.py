"""E2E fixtures: launch the demo bot as a subprocess for the duration of the
live test session, then shut it down.

Requires (in the environment / .env):
  - TEST_BOT_TOKEN : a DEDICATED test bot's token (never production).
  - TG_API_ID / TG_API_HASH / TG_SESSION : tgtest user-client credentials.
  - TG_DEFAULT_BOT : the @username of that same test bot.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

import pytest


@pytest.fixture(scope="session")
def bot_process():
    token = os.environ.get("TEST_BOT_TOKEN")
    if not token:
        pytest.skip("TEST_BOT_TOKEN not set; skipping live E2E")

    env = {**os.environ, "BOT_TOKEN": token}
    # `python -m examples.bot` here; in your own repo it would be `python -m bot`.
    proc = subprocess.Popen([sys.executable, "-m", "examples.bot"], env=env)
    try:
        time.sleep(3)  # give it time to start long polling
        if proc.poll() is not None:
            raise RuntimeError(f"bot exited during startup (code {proc.returncode})")
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
