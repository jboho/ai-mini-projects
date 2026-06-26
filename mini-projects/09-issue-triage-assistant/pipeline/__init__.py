"""AI-powered issue triage assistant over Apache JIRA-shaped data."""

import os

# Quiet noisy ML/agent stacks and prevent CrewAI's interactive tracing prompt, which
# hangs in headless runs. Must be set before crewai / tokenizers import.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
# macOS OpenMP guards (faiss/torch/onnx can segfault otherwise).
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
