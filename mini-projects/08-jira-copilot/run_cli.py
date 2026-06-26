"""Entrypoint for the Jira Copilot Typer CLI.

python run_cli.py --help
python run_cli.py sync
python run_cli.py search "oauth login"
"""

from __future__ import annotations

import jira_copilot  # noqa: F401 -- sets OpenMP / telemetry guards on import
from jira_copilot.cli.commands import app

if __name__ == "__main__":
    app()
