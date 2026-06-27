import re
from collections import defaultdict

ZONE_KEYWORDS: dict[str, list[str]] = {
    "context": ["i have", "we have", "currently", "existing", "the project", "background", "setup", "our", "been using"],
    "instruction": ["implement", "create", "write", "fix", "add", "update", "refactor", "build", "generate", "make", "convert"],
    "constraints": ["don't", "do not", "must", "never", "always", "make sure", "ensure", "avoid", "should not", "only if"],
    "examples": ["for example", "e.g.", "like this", "such as", "sample", "example:", "input:", "output:"],
}

_WORD_RE = re.compile(r"\b\w{4,}\b")


def classify_zones(prompt: str) -> dict[str, str]:
    sentences = re.split(r"(?<=[.!?\n])\s+", prompt.strip())
    buckets: dict[str, list[str]] = defaultdict(list)

    for sentence in sentences:
        lower = sentence.lower()
        matched = False
        for zone, keywords in ZONE_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                buckets[zone].append(sentence)
                matched = True
                break
        if not matched:
            buckets["instruction"].append(sentence)

    return {zone: " ".join(sents) for zone, sents in buckets.items() if sents}


def compute_engagement(zone_text: str, response: str) -> float:
    zone_words = set(_WORD_RE.findall(zone_text.lower()))
    if not zone_words:
        return 0.0
    response_words = set(_WORD_RE.findall(response.lower()))
    return len(zone_words & response_words) / len(zone_words)


def analyze_structure(pairs: list[dict]) -> dict[str, float]:
    if not pairs:
        return {}
    zone_scores: dict[str, list[float]] = defaultdict(list)
    for pair in pairs:
        zones = classify_zones(pair["prompt"])
        for zone, text in zones.items():
            zone_scores[zone].append(compute_engagement(text, pair["response"]))
    return {zone: round(sum(scores) / len(scores), 3) for zone, scores in zone_scores.items()}
