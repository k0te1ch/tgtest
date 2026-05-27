# Buttons & keyboards

**Yes — clicking inline buttons attached to a message is fully supported**, as
are reply keyboards. tgtest can assert which buttons a message exposes and
click them three different ways.

Under the hood this uses Telethon's
[`Message.click()`](https://docs.telethon.dev/en/stable/modules/custom.html#telethon.tl.custom.message.Message.click),
so clicking an **inline callback button sends the callback query to the bot**,
exactly as a real user tapping it would. Bots typically react by editing the
message in place — catch that with `expect_edit`.

## What's supported

| Capability | YAML | Python |
|------------|------|--------|
| Assert buttons present (order-free) | `buttons: [...]` in `expect`, or `expect_buttons: [...]` | `expect(buttons=[...])` / `chat.expect_buttons(...)` |
| Assert exact keyboard (set + order) | `buttons_exact: [...]`, or `expect_buttons` + `exact: true` | `expect(buttons_exact=[...])` / `expect_buttons(..., exact=True)` |
| Assert a keyboard exists / doesn't | `has_buttons: true|false` | `expect(has_buttons=...)` |
| Click by visible label | `click: "Label"` | `chat.click("Label")` |
| Click by position (0-based) | `click:` + `index: N` | `chat.click(index=N)` |
| Click by callback data | `click:` + `data: "cb"` | `chat.click(data="cb")` |

Button labels are read from **all rows** of the keyboard and flattened into a
single list, so assertions don't care about row layout (except `buttons_exact`,
which compares the flattened order).

## Inline buttons (attached to a message)

These are `InlineKeyboardMarkup` buttons rendered beneath a specific message.
The most common flow is *show → click → message edits*:

### YAML

```yaml
steps:
  - command: start
  - expect:
      contains: "Welcome"
      buttons: ["Settings", "Help"]   # assert the inline keyboard
  - click: "Settings"                 # tap the inline button
  - expect_edit:                      # bot edits the same message
      icontains: "settings"
```

### Python

```python
async with tester.conversation("@my_bot") as chat:
    await chat.send("/start")
    msg = await chat.expect(contains="Welcome", buttons=["Settings", "Help"])
    await chat.click("Settings")
    await chat.expect_edit(icontains="settings")
```

### Three ways to identify an inline button

```yaml
- click: "Settings"     # by the label the user sees
- click:
    index: 0            # by 0-based position across the flattened keyboard
- click:
    data: "settings"    # by the button's callback_data
```

```python
await chat.click("Settings")     # by label
await chat.click(index=0)        # by position
await chat.click(data="settings")  # by callback data (str is encoded to bytes)
```

Use `data=` when labels are localized or dynamic but the callback payload is
stable — it's the most robust selector for inline buttons.

## After a click

- **Callback buttons** → the bot receives a callback query. It may:
  - **edit** the message → assert with `expect_edit(...)`;
  - **send a new** message → assert with `expect(...)`;
  - **answer** with a toast/alert → `click()` returns Telethon's callback
    answer object if you need it (`answer = await chat.click("X")`).
- **URL buttons** → no callback reaches the bot; the click resolves to the URL.

If you `click` before any reply has been received, tgtest raises an
`AssertionError` ("click called before any reply was received") — there is no
"current message" to attach the click to yet.

## Reply keyboards

Reply keyboards (`ReplyKeyboardMarkup`, shown above the input box) are also
covered: their labels appear in `buttons` assertions, and clicking one sends
its text as a normal message. Selecting by label is the natural choice:

```yaml
- expect:
    has_buttons: true
- click: "Share contact"
```

## Asserting without clicking

`expect_buttons` checks the current message's keyboard without consuming a new
reply — handy after an `expect_edit` or to re-check state:

```yaml
- expect_edit:
    icontains: "settings"
- expect_buttons: ["Back", "Save"]      # still the current (edited) message
- expect_buttons: ["Back", "Save"]      # require exact order/set
  exact: true
```
