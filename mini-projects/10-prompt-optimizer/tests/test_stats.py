from optimizer.stats import compute_frequencies, extract_filler_patterns

SAMPLE_FINDINGS = [
    {"category": "filler_phrase", "excerpt": "Please make sure", "suggestion": "Remove", "confidence": "high", "source_prompt": "x"},
    {"category": "filler_phrase", "excerpt": "I need you to", "suggestion": "Remove", "confidence": "high", "source_prompt": "x"},
    {"category": "over_specified", "excerpt": "write clean code", "suggestion": "Remove", "confidence": "medium", "source_prompt": "x"},
]

CORPUS = [
    "Please make sure to create a function that reads a file and returns contents",
    "I need you to implement a class that handles database connections properly",
    "Create a test suite for the authentication module with edge cases",
    "Please make sure the output is well formatted and easy to understand",
]


def test_extract_filler_patterns_returns_only_filler_phrases():
    patterns = extract_filler_patterns(SAMPLE_FINDINGS)
    assert "Please make sure" in patterns
    assert "I need you to" in patterns
    assert "write clean code" not in patterns


def test_extract_filler_patterns_deduplicates():
    duped = SAMPLE_FINDINGS + [
        {"category": "filler_phrase", "excerpt": "Please make sure", "suggestion": "Remove", "confidence": "high", "source_prompt": "x"}
    ]
    patterns = extract_filler_patterns(duped)
    assert patterns.count("Please make sure") == 1


def test_compute_frequencies_counts_matches():
    freq = compute_frequencies(CORPUS, ["Please make sure"])
    assert freq["Please make sure"]["count"] == 2


def test_compute_frequencies_computes_percentage():
    freq = compute_frequencies(CORPUS, ["Please make sure"])
    assert freq["Please make sure"]["percentage"] == 50.0


def test_compute_frequencies_case_insensitive():
    freq = compute_frequencies(CORPUS, ["please make sure"])
    assert freq["please make sure"]["count"] == 2


def test_compute_frequencies_handles_empty_corpus():
    freq = compute_frequencies([], ["Please make sure"])
    assert freq["Please make sure"]["count"] == 0
    assert freq["Please make sure"]["percentage"] == 0.0


def test_compute_frequencies_handles_empty_patterns():
    freq = compute_frequencies(CORPUS, [])
    assert freq == {}
