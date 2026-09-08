"""Typed settings, classification taxonomy, resolution templates, impact rules."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VISUALS_DIR = PROJECT_ROOT / "visuals"

for _p in (PROJECT_ROOT / ".env", PROJECT_ROOT.parent.parent / ".env"):
    if _p.exists():
        load_dotenv(_p)
        break

# Apache projects this assistant triages (used to filter the large CSV export).
TARGET_PROJECTS = [
    "SPARK",
    "HADOOP",
    "HDFS",
    "FLINK",
    "KAFKA",
    "HIVE",
    "CASSANDRA",
    "HBASE",
    "ZOOKEEPER",
    "YARN",
]


class Settings(BaseSettings):
    # OpenAI (used in place of Groq -- the working key is OpenAI).
    openai_api_key: str = ""
    openai_base_url: str = ""
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    database_url: str = "sqlite:///data/triage.db"
    target_projects: str = ",".join(TARGET_PROJECTS)

    chunksize: int = 50_000
    llm_classify_enabled: bool = True

    # Notifications run in dry-run/simulation mode unless real credentials are set.
    notify_dry_run: bool = True
    slack_webhook_url: str = ""
    pagerduty_routing_key: str = ""
    smtp_host: str = ""

    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def project_keys(self) -> list[str]:
        return [p.strip() for p in self.target_projects.split(",") if p.strip()]


def get_settings() -> Settings:
    return Settings()


def get_model_name() -> str:
    return os.environ.get("MODEL_NAME", "gpt-4o-mini")


# --- Classification taxonomy: 13 categories ---
# Each category has high-signal keywords, regex patterns (matched case-insensitively),
# and JIRA component name fragments that map to it.
CLASSIFICATION_TAXONOMY: dict[str, dict[str, list[str]]] = {
    "memory": {
        "keywords": ["out of memory", "heap", "gc overhead", "memory leak", "oom"],
        "patterns": [r"OutOfMemoryError", r"GC overhead limit", r"java\.lang\.OutOfMemory"],
        "components": ["memory", "heap"],
    },
    "concurrency": {
        "keywords": ["deadlock", "race condition", "thread", "livelock", "concurrent"],
        "patterns": [r"deadlock", r"ConcurrentModificationException", r"race condition"],
        "components": ["threading", "scheduler"],
    },
    "data_processing": {
        "keywords": ["null pointer", "parse", "corrupt", "invalid record", "schema mismatch"],
        "patterns": [r"NullPointerException", r"NumberFormatException", r"ArrayIndexOutOfBounds"],
        "components": ["sql", "core", "parser"],
    },
    "network": {
        "keywords": ["timeout", "connection refused", "socket", "unreachable", "rpc"],
        "patterns": [r"SocketTimeoutException", r"ConnectException", r"Connection refused"],
        "components": ["rpc", "network", "transport"],
    },
    "io_storage": {
        "keywords": ["disk full", "file not found", "no space", "corrupt block", "checksum"],
        "patterns": [r"IOException", r"FileNotFoundException", r"No space left on device"],
        "components": ["hdfs", "storage", "filesystem"],
    },
    "configuration": {
        "keywords": ["misconfigured", "property", "setting", "config", "missing parameter"],
        "patterns": [
            r"ConfigException",
            r"IllegalArgumentException.*config",
            r"property .* not set",
        ],
        "components": ["config", "conf"],
    },
    "dependency": {
        "keywords": ["classnotfound", "version conflict", "incompatible jar", "missing dependency"],
        "patterns": [r"ClassNotFoundException", r"NoClassDefFoundError", r"NoSuchMethodError"],
        "components": ["build", "dependencies"],
    },
    "performance": {
        "keywords": ["slow", "latency", "bottleneck", "high cpu", "regression"],
        "patterns": [r"performance regression", r"took \d+ ?(ms|s|seconds)", r"slow query"],
        "components": ["performance", "optimizer"],
    },
    "security": {
        "keywords": [
            "authentication",
            "permission denied",
            "vulnerability",
            "unauthorized",
            "kerberos",
        ],
        "patterns": [r"AccessControlException", r"AuthenticationException", r"CVE-\d{4}-\d+"],
        "components": ["security", "auth"],
    },
    "api_compatibility": {
        "keywords": ["deprecated", "breaking change", "api change", "backward compatibility"],
        "patterns": [r"deprecated", r"UnsupportedOperationException", r"incompatible API"],
        "components": ["api", "client"],
    },
    "build": {
        "keywords": ["compile error", "build failure", "maven", "gradle", "test failure"],
        "patterns": [r"BUILD FAILURE", r"compilation failed", r"cannot find symbol"],
        "components": ["build", "ci"],
    },
    "serialization": {
        "keywords": ["serialization", "deserialize", "kryo", "avro", "protobuf"],
        "patterns": [
            r"NotSerializableException",
            r"SerializationException",
            r"InvalidClassException",
        ],
        "components": ["serde", "serialization"],
    },
    "other": {"keywords": [], "patterns": [], "components": []},
}

CATEGORIES = list(CLASSIFICATION_TAXONOMY.keys())

# Composite pattern rules (medium confidence): all fragments must appear in the text.
COMPOSITE_PATTERNS: list[tuple[list[str], str]] = [
    (["gc", "pause"], "memory"),
    (["thread", "blocked"], "concurrency"),
    (["retry", "timeout"], "network"),
    (["shuffle", "fetch"], "network"),
    (["spill", "disk"], "io_storage"),
]

RESOLUTION_TEMPLATES: dict[str, str] = {
    "memory": "Increase heap/executor memory and review object retention; profile with a heap dump.",
    "concurrency": "Audit lock ordering and shared state; add timeouts and reproduce under load.",
    "data_processing": "Add null/format guards and validate input schema; add a regression test.",
    "network": "Add retries with backoff and tune timeouts; verify connectivity and DNS.",
    "io_storage": "Check disk capacity and permissions; validate checksums and clean stale files.",
    "configuration": "Correct the misconfigured property and document the expected value/range.",
    "dependency": "Align dependency versions and rebuild; check the classpath/shading.",
    "performance": "Profile the hot path, add caching/indexes, and benchmark before/after.",
    "security": "Fix the auth/permission gap, rotate credentials, and add an access test.",
    "api_compatibility": "Provide a compatibility shim or deprecation path; update the migration guide.",
    "build": "Fix the compilation/test break and pin the toolchain version.",
    "serialization": "Ensure types are serializable and register custom serializers; version the schema.",
    "other": "Investigate with full context; gather logs and a minimal reproduction.",
}

# Action impact governs auto-approval. LOW auto-approves; MEDIUM/HIGH need a human.
IMPACT_RULES: dict[str, str] = {
    "add_label": "LOW",
    "set_priority": "LOW",
    "set_component": "LOW",
    "add_comment": "LOW",
    "reassign": "MEDIUM",
    "transition_status": "MEDIUM",
    "link_issues": "MEDIUM",
    "bulk_update": "HIGH",
    "cross_project_update": "HIGH",
    "close_issue": "HIGH",
}
