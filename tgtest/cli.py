"""Command-line runner: `python -m tgtest run scenarios/`.

Discovers YAML scenarios, runs them against the configured bot, and prints a
per-scenario PASS/FAIL summary. Exit code is non-zero if any scenario fails so
it slots into CI.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time

from .config import Settings
from .logger import configure_logger
from .client import BotTester
from .scenario import load_scenarios, Scenario
from .engine import run_scenario
from .exceptions import StepError, ScenarioError

GREEN, RED, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"

_log = logging.getLogger(__name__)


def _c(text: str, color: str, use_color: bool) -> str:
    return f"{color}{text}{RESET}" if use_color else text


async def _run_all(scenarios: list[Scenario], config: Settings, use_color: bool) -> int:
    logger = configure_logger(config)
    passed = failed = 0
    async with BotTester.create(config) as tester:
        for sc in scenarios:
            logger.info("Running scenario: %s", sc.name)
            label = f"{sc.name}" + (f" [{sc.source}]" if sc.source else "")
            start = time.monotonic()
            try:
                await run_scenario(tester, sc)
            except StepError as exc:
                failed += 1
                dur = time.monotonic() - start
                print(f"{_c('FAIL', RED, use_color)} {label} ({dur:.1f}s)")
                loc = f"step {exc.step_index}"
                if exc.step_desc:
                    loc += f" — {exc.step_desc}"
                print(_c(f"      {loc}", DIM, use_color))
                for line in str(exc).splitlines():
                    print(_c(f"      {line}", RED, use_color))
                logger.error("FAIL %s at step %s: %s", sc.name, exc.step_index, exc)
            except Exception as exc:
                failed += 1
                dur = time.monotonic() - start
                print(f"{_c('ERROR', RED, use_color)} {label} ({dur:.1f}s)")
                print(_c(f"      {type(exc).__name__}: {exc}", RED, use_color))
                logger.exception("ERROR %s: %s", sc.name, exc)
            else:
                passed += 1
                dur = time.monotonic() - start
                print(f"{_c('PASS', GREEN, use_color)} {label} ({dur:.1f}s)")
                logger.info("PASS %s (%.1fs)", sc.name, dur)

    total = passed + failed
    summary = f"\n{passed}/{total} passed"
    print(_c(summary, GREEN if not failed else RED, use_color))
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tgtest", description="Telegram bot E2E test runner"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="run YAML scenarios")
    run.add_argument("paths", nargs="+", help="scenario files, dirs, or globs")
    run.add_argument("--bot", help="override bot for all scenarios")
    run.add_argument("--env", help="path to a .env file")
    run.add_argument("--no-color", action="store_true", help="disable colored output")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        try:
            config = Settings.load(env_file=args.env)
        except RuntimeError as exc:
            _log.error("config error: %s", exc)
            return 2
        try:
            scenarios = load_scenarios(args.paths)
        except ScenarioError as exc:
            _log.error("scenario error: %s", exc)
            return 2
        if args.bot:
            for sc in scenarios:
                sc.bot = args.bot
        if not scenarios:
            print("no scenarios found", file=sys.stderr)
            return 2
        use_color = not args.no_color and sys.stdout.isatty()
        return asyncio.run(_run_all(scenarios, config, use_color))
    return 2


if __name__ == "__main__":
    sys.exit(main())
