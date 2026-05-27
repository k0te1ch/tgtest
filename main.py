"""Application entry point.

Loads settings, configures logging, then delegates to the tgtest CLI so that
`python main.py run scenarios/` behaves identically to `python -m tgtest run`.
"""
import sys

from tgtest.cli import main as cli_main

if __name__ == "__main__":
    sys.exit(cli_main())
