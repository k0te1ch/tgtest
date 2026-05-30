"""Exception hierarchy for tgtest."""


class TgTestError(Exception):
    """Base class for all tgtest errors."""


class ScenarioError(TgTestError):
    """Raised when a YAML scenario is malformed or cannot be parsed."""


class StepError(TgTestError):
    """Raised when a scenario step fails (assertion failed or timed out).

    Carries the step index and a human-readable description so the runner can
    report exactly which step in which scenario broke.
    """

    def __init__(
        self,
        message: str,
        *,
        step_index: int | None = None,
        step_desc: str | None = None,
    ):
        self.step_index = step_index
        self.step_desc = step_desc
        super().__init__(message)
