from optimizer.structure import classify_zones, compute_engagement, analyze_structure

PROMPT_WITH_CONTEXT = "I have a Python project. Currently we use SQLAlchemy for the database. Please implement a new endpoint that creates a user record. Make sure it validates the email field. Don't break existing tests."
RESPONSE = "Here is the endpoint implementation with email validation."


def test_classify_zones_returns_dict():
    zones = classify_zones(PROMPT_WITH_CONTEXT)
    assert isinstance(zones, dict)


def test_classify_zones_identifies_constraint_zone():
    zones = classify_zones(PROMPT_WITH_CONTEXT)
    combined = " ".join(zones.values()).lower()
    assert "don't" in combined or "make sure" in combined


def test_classify_zones_zone_keys_are_valid():
    zones = classify_zones(PROMPT_WITH_CONTEXT)
    valid_keys = {"context", "instruction", "constraints", "examples"}
    assert set(zones.keys()).issubset(valid_keys)


def test_compute_engagement_high_for_matching_text():
    score = compute_engagement("email validation endpoint", "endpoint implementation with email validation")
    assert score > 0.5


def test_compute_engagement_low_for_irrelevant_text():
    score = compute_engagement("currently using legacy mysql database setup", "Here is the endpoint code")
    assert score < 0.3


def test_compute_engagement_returns_zero_for_empty_zone():
    score = compute_engagement("", "some response text here")
    assert score == 0.0


def test_analyze_structure_returns_zone_scores():
    pairs = [
        {"prompt": PROMPT_WITH_CONTEXT, "response": RESPONSE},
        {"prompt": PROMPT_WITH_CONTEXT, "response": RESPONSE},
    ]
    scores = analyze_structure(pairs)
    assert isinstance(scores, dict)
    for key in scores:
        assert isinstance(scores[key], float)
        assert 0.0 <= scores[key] <= 1.0


def test_analyze_structure_handles_empty_pairs():
    scores = analyze_structure([])
    assert scores == {}
