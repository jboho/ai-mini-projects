"""Core (pure, LLM-free) computation layer for the digital clone.

Guards for the macOS faiss/torch OpenMP conflict and quiets CrewAI telemetry.
"""

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
