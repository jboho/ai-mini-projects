import json
from pathlib import Path

MIN_WORD_COUNT = 15


def _extract_text(content: list) -> str | None:
    if not isinstance(content, list):
        return None
    blocks = [b for b in content if isinstance(b, dict)]
    if any(b.get("type") == "tool_result" for b in blocks):
        return None
    parts = [b["text"] for b in blocks if b.get("type") == "text" and b.get("text")]
    return " ".join(parts).strip() if parts else None


def _process_message(obj: dict, pending: list) -> dict | None:
    if obj.get("isSidechain"):
        return None
    content = obj.get("message", {}).get("content", [])
    msg_type = obj.get("type")

    if msg_type == "user":
        text = _extract_text(content)
        if text and len(text.split()) >= MIN_WORD_COUNT:
            pending.clear()
            pending.append(text)
        return None

    if msg_type == "assistant" and pending:
        text = _extract_text(content)
        if text:
            prompt = pending.pop()
            return {"prompt": prompt, "response": text}
    return None


def load_pairs_from_file(path: Path) -> list[dict]:
    pairs = []
    pending: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        result = _process_message(obj, pending)
        if result:
            pairs.append(result)
    return pairs


def load_all_pairs(transcripts_dir: Path) -> list[dict]:
    if not transcripts_dir.exists():
        return []
    pairs = []
    for jsonl_file in transcripts_dir.rglob("*.jsonl"):
        pairs.extend(load_pairs_from_file(jsonl_file))
    return pairs
