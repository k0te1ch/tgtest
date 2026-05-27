# CLI

The runner executes YAML scenarios and prints a per-scenario result summary.

Source: [`tgtest/cli.py`](../tgtest/cli.py).

## Invocation

All three forms are equivalent:

```powershell
poetry run tgtest run <paths...>     # console script (from pyproject)
python -m tgtest run <paths...>      # module
python main.py run <paths...>        # entry-point script
```

## `tgtest run`

```
tgtest run PATHS... [--bot BOT] [--env FILE] [--no-color]
```

| Argument | Description |
|----------|-------------|
| `PATHS...` | One or more scenario files, directories, or globs. Directories are searched recursively for `*.yaml` / `*.yml`. |
| `--bot BOT` | Override the target bot for **all** scenarios (e.g. `@staging_bot`). |
| `--env FILE` | Load configuration from a specific `.env` file. |
| `--no-color` | Disable ANSI colors (also auto-disabled when output is not a TTY). |

### Examples

```powershell
poetry run tgtest run scenarios/                      # whole directory, recursive
poetry run tgtest run scenarios/start.yaml            # a single file
poetry run tgtest run "scenarios/smoke_*.yaml"        # a glob
poetry run tgtest run scenarios/ --bot @staging_bot   # point everything elsewhere
poetry run tgtest run scenarios/ --env .env.ci        # alternate credentials
```

## Output

Each scenario prints one line — `PASS`, `FAIL`, or `ERROR` — with its duration.
A failure also prints the offending step (index + description) and a diff-style
reason. Example:

```
PASS Start shows the menu [scenarios/start.yaml] (1.2s)
FAIL Unknown command rejected [scenarios/start.yaml] (0.4s)
      step 1 — expect: {'icontains': 'unknown'}
      expect(icontains='unknown') failed:
        text does not contain (ci) 'unknown'
        actual: 'Sorry?'

1/2 passed
```

Runs are also logged to `logs/tgtest.log`.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | All scenarios passed. |
| `1` | One or more scenarios failed or errored. |
| `2` | Usage / config / scenario-parse error (bad credentials, no scenarios, malformed YAML). |

The non-zero codes make the runner CI-friendly: a failing suite fails the job.
