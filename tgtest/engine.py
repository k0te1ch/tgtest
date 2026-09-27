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


class _Steps:
    """One method per YAML action; the method name is the action key."""

    def __init__(self, chat, value, opts: dict, timeout: float | None):
        self.chat = chat
        self.value = value
        self.opts = opts
        self.timeout = timeout

    async def send(self):
        await self.chat.send(str(self.value))

    async def send_file(self):
        await self.chat.send_file(
            str(self.value),
            caption=self.opts.get("caption"),
            force_document=bool(self.opts.get("force_document", False)),
        )

    async def command(self):
        await self.chat.command(str(self.value))

    async def sleep(self):
        await asyncio.sleep(float(self.value))

    async def expect(self):
        message = await self.chat.get_reply(timeout=self.timeout)
        reason = Matcher.from_spec(self.value).check(message)
        if reason:
            raise AssertionError(reason)

    async def expect_edit(self):
        await self.chat.expect_edit(timeout=self.timeout, **_as_spec(self.value))

    async def wait_until(self):
        await self.chat.wait_until(timeout=self.timeout, **_as_spec(self.value))

    async def expect_no_reply(self):
        if self.value is not None:
            within = float(self.value)
        else:
            within = float(self.opts.get("within", 2.0))
        await self.chat.expect_no_reply(within=within)

    async def expect_buttons(self):
        labels = self.value if isinstance(self.value, list) else [self.value]
        self.chat.expect_buttons(*labels, exact=bool(self.opts.get("exact", False)))

    async def click(self):
        await self.chat.click(
            text=self.value if isinstance(self.value, str) else None,
            index=self.opts.get("index"),
            data=self.opts.get("data"),
        )


async def _run_step(chat, step: Step):
    action, value, opts = step.action, step.value, step.options
    timeout = float(opts["timeout"]) if "timeout" in opts else None
    handler = getattr(_Steps(chat, value, opts, timeout), action, None)
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
