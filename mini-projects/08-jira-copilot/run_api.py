"""Launch the Jira Copilot FastAPI app with uvicorn.

python run_api.py            # serve on 127.0.0.1:8000
python run_api.py --port 9000
"""

from __future__ import annotations

import argparse

import jira_copilot  # noqa: F401 -- sets OpenMP / telemetry guards on import


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Jira Copilot API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("jira_copilot.api.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
