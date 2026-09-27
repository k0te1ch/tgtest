"""expect_edit, wait_until and button callback data against fake messages."""

from dataclasses import dataclass, field
from datetime import datetime

import pytest

from tgtest.client import _Chat
from tgtest.engine import _Steps
from tgtest.matchers import Matcher
from tgtest.scenario import _parse_step


@dataclass
class Button:
    text: str
    data: bytes | None = None


@dataclass
class Message:
    text: str
    buttons: list = field(default_factory=list)
    edit_date: datetime | None = None
    id: int = 7


class FakeClient:
    """Serves the message as it looks on each read; the last state repeats."""

    def __init__(self, *states: Message):
        self.states = list(states)
        self.reads = 0

    async def get_messages(self, chat, ids):
        self.reads += 1
        return self.states.pop(0) if len(self.states) > 1 else self.states[0]


def chat_with(current: Message, *states: Message) -> _Chat:
    chat = _Chat(None, "bot", 0.2, client=FakeClient(*states), poll_interval=0.01)
    chat.last = current
    return chat


def edited(text: str, buttons=(), second: int = 1) -> Message:
    return Message(text, list(buttons), edit_date=datetime(2026, 1, 1, 0, 0, second))


async def test_edit_that_landed_before_the_call_is_seen():
    chat = chat_with(Message("Menu"), edited("Settings"))

    message = await chat.expect_edit(equals="Settings")

    assert message.text == "Settings"
    assert chat.last.text == "Settings"


async def test_expect_edit_waits_for_the_matching_edit():
    chat = chat_with(
        Message("Upload"),
        Message("Upload"),
        edited("Uploading 40%", second=1),
        edited("Uploaded", second=2),
    )

    await chat.expect_edit(contains="Uploaded")

    assert chat._client.reads == 3


async def test_expect_edit_times_out_without_an_edit():
    chat = chat_with(Message("Menu"), Message("Menu"))

    with pytest.raises(AssertionError, match="(?s)waiting for an edit.*not edited"):
        await chat.expect_edit(contains="Settings")


async def test_expect_edit_reports_the_last_mismatch():
    chat = chat_with(Message("Menu"), edited("Oops"))

    with pytest.raises(AssertionError, match="Oops"):
        await chat.expect_edit(equals="Settings")


async def test_keyboard_only_edit_counts():
    before = Message("Menu", [[Button("FTP", b"ftp")]])
    after = Message("Menu", [[Button("Upload", b"upload")]])
    chat = chat_with(before, after)

    await chat.expect_edit(buttons=["Upload"])


async def test_wait_until_accepts_an_already_matching_message():
    chat = chat_with(Message("Done"), Message("Done"))

    await chat.wait_until(contains="Done")


async def test_wait_until_polls_until_the_text_appears():
    chat = chat_with(Message("Sending"), Message("Sending"), edited("Uploaded OK"))

    await chat.wait_until(contains="Uploaded")


async def test_yaml_wait_until_step():
    chat = chat_with(Message("Sending"), edited("Uploaded OK"))
    step = _parse_step({"wait_until": {"contains": "OK"}, "timeout": 1}, 0)

    await getattr(_Steps(chat, step.value, step.options, 1.0), step.action)()


MENU = Message(
    "Menu",
    [[Button("Episode", b"type:episode"), Button("Aftershow", b"type:after")]],
)


def test_buttons_match_by_callback_data():
    assert (
        Matcher.from_spec(
            {"buttons": [{"text": "Episode", "data": "type:episode"}]}
        ).check(MENU)
        is None
    )
    assert (
        Matcher.from_spec({"buttons": [{"data_regex": "^type:"}]}).check(MENU) is None
    )


def test_wrong_callback_data_is_reported_with_the_keyboard():
    reason = Matcher.from_spec({"buttons": [{"text": "Episode", "data": "ep"}]}).check(
        MENU
    )

    assert "missing buttons" in reason
    assert "'Episode' ('type:episode')" in reason


def test_expect_buttons_accepts_data_specs():
    chat = chat_with(MENU)

    chat.expect_buttons("Aftershow", {"data": "type:episode"})
    with pytest.raises(AssertionError, match="missing buttons"):
        chat.expect_buttons({"text": "Aftershow", "data": "type:episode"})
    chat.expect_buttons("Episode", {"text": "Aftershow"}, exact=True)


async def test_wait_for_text_ignores_case_and_polls():
    chat = chat_with(
        Message("Отправка"), Message("Отправка"), edited("Файл УСПЕШНО загружен")
    )

    message = await chat.wait_for_text("успешно загружен")

    assert message.text == "Файл УСПЕШНО загружен"


async def test_wait_for_text_takes_any_message():
    chat = chat_with(Message("first"), edited("status: done"))
    status = Message("status: working", id=9)

    message = await chat.wait_for_text("DONE", message=status)

    assert chat.last is message


async def test_wait_for_text_times_out_with_the_last_text():
    chat = chat_with(Message("working"), Message("still working"))

    with pytest.raises(AssertionError, match="still working"):
        await chat.wait_for_text("done", timeout=0.05)


def test_icontains_ignores_case_both_ways():
    assert (
        Matcher.from_spec({"icontains": "ГОТОВО"}).check(Message("всё готово")) is None
    )
    assert Matcher.from_spec({"icontains": "done"}).check(Message("DONE!")) is None
