def extract_filler_patterns(findings: list[dict]) -> list[str]:
    """Extract unique filler phrases from audit findings."""
    seen = set()
    patterns = []
    for f in findings:
        if f.get("category") == "filler_phrase":
            excerpt = f.get("excerpt", "").strip()
            if excerpt and excerpt not in seen:
                seen.add(excerpt)
                patterns.append(excerpt)
    return patterns


def compute_frequencies(corpus: list[str], patterns: list[str]) -> dict:
    """Count and compute percentage frequency of patterns in corpus."""
    if not patterns:
        return {}
    total = len(corpus)
    result = {}
    for pattern in patterns:
        lower_pattern = pattern.lower()
        count = sum(1 for prompt in corpus if lower_pattern in prompt.lower())
        result[pattern] = {
            "count": count,
            "percentage": round(count / total * 100, 1) if total > 0 else 0.0,
        }
    return result
