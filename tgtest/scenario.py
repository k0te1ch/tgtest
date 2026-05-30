"""Parse YAML scenario files into a validated Scenario model.

A scenario file looks like:

    name: Start shows menu
    bot: "@my_bot"        # optional; falls back to TG_DEFAULT_BOT
    timeout: 15            # optional per-step default
    steps:
      - send: "/start"
      - expect:
          contains: "Welcome"
          buttons: ["Settings", "Help"]
      - click: "Settings"
      - expect_edit:
          contains: "Settings menu"

A single file may hold multiple scenarios using YAML's `---` document
separator, so one file can be a whole suite.
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field

import yaml

from .exceptions import ScenarioError

# Recognised step keys. Each step dict must have exactly one *action* key
# (plus optional modifiers like `timeout`).
_ACTION_KEYS = {
    "send",
    "command",
    "expect",
    "expect_edit",
    "expect_no_reply",
    "expect_buttons",
    "click",
    "sleep",
}
_MODIFIER_KEYS = {"timeout", "exact", "index", "data", "note", "within"}


@dataclass
class Step:
    action: str
    value: object
    options: dict = field(default_factory=dict)
    index: int = 0

    def describe(self) -> str:
        note = self.options.get("note")
        if self.value is not None:
            base = f"{self.action}: {self.value!r}"
        else:
            base = self.action
        return f"{base}  # {note}" if note else base


@dataclass
class Scenario:
    name: str
    steps: list[Step]
    bot: str | None = None
    timeout: float | None = None
    source: str | None = None  # file path, for reporting


def _parse_step(raw: dict, idx: int) -> Step:
    if not isinstance(raw, dict):
        raise ScenarioError(f"step {idx} must be a mapping, got {type(raw).__name__}")
    actions = [k for k in raw if k in _ACTION_KEYS]
    if len(actions) != 1:
        raise ScenarioError(
            f"step {idx} must have exactly one action key "
            f"({', '.join(sorted(_ACTION_KEYS))}); got {actions or 'none'}"
        )
    action = actions[0]
    unknown = set(raw) - _ACTION_KEYS - _MODIFIER_KEYS
    if unknown:
        joined = ", ".join(sorted(unknown))
        raise ScenarioError(f"step {idx} has unknown keys: {joined}")
    options = {k: raw[k] for k in raw if k in _MODIFIER_KEYS}
    return Step(action=action, value=raw[action], options=options, index=idx)


def _parse_doc(doc: dict, source: str | None) -> Scenario:
    if not isinstance(doc, dict):
        raise ScenarioError(f"scenario must be a mapping, got {type(doc).__name__}")
    if "steps" not in doc or not isinstance(doc["steps"], list):
        raise ScenarioError("scenario must have a 'steps' list")
    steps = [_parse_step(s, i) for i, s in enumerate(doc["steps"])]
    return Scenario(
        name=doc.get("name") or (os.path.basename(source) if source else "unnamed"),
        steps=steps,
        bot=doc.get("bot"),
        timeout=float(doc["timeout"]) if "timeout" in doc else None,
        source=source,
    )


def load_scenario(path: str) -> list[Scenario]:
    """Load all scenarios from one YAML file (supports multi-document files)."""
    with open(path, "r", encoding="utf-8") as fh:
        try:
            docs = list(yaml.safe_load_all(fh))
        except yaml.YAMLError as exc:
            raise ScenarioError(f"{path}: invalid YAML: {exc}") from exc
    scenarios = []
    for doc in docs:
        if doc is None:
            continue
        try:
            scenarios.append(_parse_doc(doc, source=path))
        except ScenarioError as exc:
            raise ScenarioError(f"{path}: {exc}") from exc
    if not scenarios:
        raise ScenarioError(f"{path}: no scenarios found")
    return scenarios


def load_scenarios(paths: list[str]) -> list[Scenario]:
    """Expand file/dir/glob paths into a flat list of scenarios.

    Directories are searched recursively for *.yaml / *.yml files.
    """
    files: list[str] = []
    for p in paths:
        if os.path.isdir(p):
            for ext in ("yaml", "yml"):
                files.extend(
                    sorted(glob.glob(os.path.join(p, "**", f"*.{ext}"), recursive=True))
                )
        elif any(ch in p for ch in "*?[]"):
            files.extend(sorted(glob.glob(p, recursive=True)))
        else:
            files.append(p)
    scenarios: list[Scenario] = []
    for f in files:
        scenarios.extend(load_scenario(f))
    return scenarios
