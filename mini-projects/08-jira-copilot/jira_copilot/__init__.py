"""AI-powered Jira copilot over the TAWOS dataset."""

import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
# Silence CrewAI telemetry + first-run interactive tracing prompt (would hang headless).
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
