"""Execute a parsed Scenario against a live BotTester conversation.

The engine maps each YAML step to a call on the `_Chat` helper. All assertion
failures and timeouts are wrapped in StepError with the offending step's index
and description, so the runner can pinpoint failures.
"""

from __future__ import annotations

import asyncio

from .client import BotTester
from .matchers import Matcher
from .scenario import Scenario, Step
from .exceptions import StepError


def _build_handlers(chat, value, opts, timeout) -> dict:
    async def _send():
        await chat.send(str(value))

    async def _command():
        await chat.command(str(value))

    async def _sleep():
        await asyncio.sleep(float(value))

    async def _expect():
        message = await chat.get_reply(timeout=timeout)
        reason = Matcher.from_spec(value).check(message)
        if reason:
            raise AssertionError(reason)

    async def _expect_edit():
        await chat.expect_edit(timeout=timeout, **(_as_spec(value)))

    async def _expect_no_reply():
        within = float(value) if value is not None else float(opts.get("within", 2.0))
        await chat.expect_no_reply(within=within)

    async def _expect_buttons():
        labels = value if isinstance(value, list) else [value]
        chat.expect_buttons(*labels, exact=bool(opts.get("exact", False)))

    async def _click():
        await chat.click(
            text=value if isinstance(value, str) else None,
            index=opts.get("index"),
            data=opts.get("data"),
        )

    return {
        "send": _send,
        "command": _command,
        "sleep": _sleep,
        "expect": _expect,
        "expect_edit": _expect_edit,
        "expect_no_reply": _expect_no_reply,
        "expect_buttons": _expect_buttons,
        "click": _click,
    }


async def _run_step(chat, step: Step):
    action, value, opts = step.action, step.value, step.options
    timeout = float(opts["timeout"]) if "timeout" in opts else None
    handler = _build_handlers(chat, value, opts, timeout).get(action)
    if handler is None:  # pragma: no cover - parser guarantees valid actions
        raise StepError(f"unknown action {action!r}", step_index=step.index)
    await handler()


def _as_spec(value):
    """expect_edit accepts the same shorthand as expect (string or dict)."""
    if value is None:
        return {}
    if isinstance(value, str):
        return {"equals": value}
    return dict(value)


async def run_scenario(tester: BotTester, scenario: Scenario):
    """Run every step of a scenario. Raises StepError on the first failure."""
    async with tester.conversation(scenario.bot, timeout=scenario.timeout) as chat:
        for step in scenario.steps:
            try:
                await _run_step(chat, step)
            except AssertionError as exc:
                raise StepError(
                    str(exc), step_index=step.index, step_desc=step.describe()
                ) from exc
            except StepError:
                raise
            except Exception as exc:  # surface unexpected errors with step context
                raise StepError(
                    f"{type(exc).__name__}: {exc}",
                    step_index=step.index,
                    step_desc=step.describe(),
                ) from exc
