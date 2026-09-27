"""Text and button matchers shared by the engine and the Python helper API.

A matcher is built from a dict (the body of an `expect` step) and applied to a
Telethon Message. It returns None on success or a human-readable failure
reason string. Keeping failures as strings (rather than raising) lets the
caller assemble a single rich StepError with full context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Keys in an expect block that describe the message *text*.
_TEXT_KEYS = ("equals", "contains", "icontains", "regex", "iregex", "not_contains")


def _message_text(message) -> str:
    """Best-effort textual content of a message (text, or media caption)."""
    return getattr(message, "text", None) or getattr(message, "message", None) or ""


def button_texts(message) -> list[str]:
    """Flatten an inline/reply keyboard into a list of button label strings."""
    return [text for text, _ in keyboard(message)]


def keyboard(message) -> list[tuple[str, str | None]]:
    """Flatten a keyboard into (label, callback data) pairs.

    Callback data is decoded to text; buttons without it (URL, reply
    keyboards) get None.
    """
    pairs: list[tuple[str, str | None]] = []
    for row in getattr(message, "buttons", None) or []:
        for btn in row:
            text = getattr(btn, "text", None)
            if text is None:
                continue
            data = getattr(btn, "data", None)
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="replace")
            pairs.append((text, data))
    return pairs


def _button_matches(expected, text: str, data: str | None) -> bool:
    """`expected` is a label, or a mapping with text / data / data_regex."""
    if isinstance(expected, str):
        return text == expected
    if "text" in expected and text != expected["text"]:
        return False
    if "data" in expected and data != expected["data"]:
        return False
    if "data_regex" in expected and (
        data is None or not re.search(expected["data_regex"], data)
    ):
        return False
    return True


def missing_buttons(expected: list, message) -> list:
    """The entries of `expected` that no button on `message` satisfies."""
    actual = keyboard(message)
    return [
        want
        for want in expected
        if not any(_button_matches(want, text, data) for text, data in actual)
    ]


def describe_keyboard(message) -> str:
    return ", ".join(
        f"{text!r}" if data is None else f"{text!r} ({data!r})"
        for text, data in keyboard(message)
    )


@dataclass
class Matcher:
    equals: str | None = None
    contains: str | None = None
    icontains: str | None = None
    not_contains: str | None = None
    regex: str | None = None
    iregex: str | None = None
    # buttons that must all be present: labels, or {text, data, data_regex}
    buttons: list | None = None
    buttons_exact: list[str] | None = None  # full keyboard must equal this set/order
    has_buttons: bool | None = None  # assert presence/absence of any keyboard
    _raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_spec(cls, spec) -> "Matcher":
        """Build a Matcher from a YAML `expect` value.

        Accepts a plain string (shorthand for `equals`) or a dict of keys.
        """
        if spec is None:
            return cls(_raw={})
        if isinstance(spec, str):
            return cls(equals=spec, _raw={"equals": spec})
        if not isinstance(spec, dict):
            raise ValueError(
                f"expect must be a string or mapping, got {type(spec).__name__}"
            )
        known = {
            "equals",
            "contains",
            "icontains",
            "not_contains",
            "regex",
            "iregex",
            "buttons",
            "buttons_exact",
            "has_buttons",
        }
        unknown = set(spec) - known
        if unknown:
            raise ValueError(f"unknown expect keys: {', '.join(sorted(unknown))}")
        return cls(
            equals=spec.get("equals"),
            contains=spec.get("contains"),
            icontains=spec.get("icontains"),
            not_contains=spec.get("not_contains"),
            regex=spec.get("regex"),
            iregex=spec.get("iregex"),
            buttons=spec.get("buttons"),
            buttons_exact=spec.get("buttons_exact"),
            has_buttons=spec.get("has_buttons"),
            _raw=dict(spec),
        )

    def check(self, message) -> str | None:
        """Return None if the message satisfies every clause, else a reason."""
        return self._check_text(_message_text(message)) or self._check_buttons(message)

    def _check_text(self, text: str) -> str | None:
        if self.equals is not None and text != self.equals:
            return f"text != equals\n  expected: {self.equals!r}\n  actual:   {text!r}"
        if self.contains is not None and self.contains not in text:
            return f"text does not contain {self.contains!r}\n  actual: {text!r}"
        if self.icontains is not None and self.icontains.lower() not in text.lower():
            return f"text does not contain (ci) {self.icontains!r}\n  actual: {text!r}"
        if self.not_contains is not None and self.not_contains in text:
            return (
                f"text unexpectedly contains {self.not_contains!r}\n  actual: {text!r}"
            )
        if self.regex is not None and not re.search(self.regex, text):
            return f"text does not match regex {self.regex!r}\n  actual: {text!r}"
        if self.iregex is not None and not re.search(self.iregex, text, re.IGNORECASE):
            return f"text does not match regex (ci) {self.iregex!r}\n  actual: {text!r}"
        return None

    def _check_buttons(self, message) -> str | None:
        actual = button_texts(message)
        if self.has_buttons is not None and bool(actual) != self.has_buttons:
            return (
                f"has_buttons expected {self.has_buttons}, "
                f"got {bool(actual)} (buttons={actual})"
            )
        if self.buttons is not None:
            missing = missing_buttons(self.buttons, message)
            if missing:
                return (
                    f"missing buttons {missing}\n"
                    f"  actual buttons: {describe_keyboard(message)}"
                )
        if self.buttons_exact is not None and actual != list(self.buttons_exact):
            return (
                f"buttons differ\n  expected: {list(self.buttons_exact)}\n"
                f"  actual:   {actual}"
            )
        return None

    def describe(self) -> str:
        parts = [f"{k}={v!r}" for k, v in self._raw.items()]
        return "expect(" + ", ".join(parts) + ")" if parts else "expect(any reply)"
