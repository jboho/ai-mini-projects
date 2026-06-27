from optimizer.report import generate_report

AUDIT_FINDINGS = [
    {
        "category": "filler_phrase",
        "excerpt": "Please make sure to",
        "suggestion": "Remove — the model applies care by default.",
        "confidence": "high",
        "source_prompt": "Please make sure to implement a read_file function that returns file contents as a string.",
    },
    {
        "category": "over_specified",
        "excerpt": "write clean code",
        "suggestion": "Remove — implied by default behavior.",
        "confidence": "medium",
        "source_prompt": "write clean code for the parser",
    },
    {
        "category": "ignored_instruction",
        "excerpt": "add docstrings",
        "suggestion": "The response did not include docstrings; this instruction was ignored.",
        "confidence": "low",
        "source_prompt": "add docstrings to all functions",
    },
]

FREQ_TABLE = {
    "Please make sure to": {"count": 14, "percentage": 70.0},
    "I need you to": {"count": 8, "percentage": 40.0},
}

ZONE_STATS = {
    "context": 0.12,
    "instruction": 0.61,
    "constraints": 0.08,
}


def test_generate_report_returns_string():
    report = generate_report(AUDIT_FINDINGS, FREQ_TABLE, ZONE_STATS)
    assert isinstance(report, str)


def test_generate_report_contains_executive_summary():
    report = generate_report(AUDIT_FINDINGS, FREQ_TABLE, ZONE_STATS)
    assert "Executive Summary" in report


def test_generate_report_contains_rewrite_examples():
    report = generate_report(AUDIT_FINDINGS, FREQ_TABLE, ZONE_STATS)
    assert "Please make sure to" in report
    assert "write clean code" in report


def test_generate_report_excludes_low_confidence_from_examples():
    report = generate_report(AUDIT_FINDINGS, FREQ_TABLE, ZONE_STATS)
    lines = report.splitlines()
    example_section_start = next(i for i, l in enumerate(lines) if "Rewrite Examples" in l)
    freq_section_start = next(i for i, l in enumerate(lines) if "Frequency" in l)
    example_lines = "\n".join(lines[example_section_start:freq_section_start])
    assert "add docstrings" not in example_lines


def test_generate_report_contains_frequency_table():
    report = generate_report(AUDIT_FINDINGS, FREQ_TABLE, ZONE_STATS)
    assert "70.0%" in report
    assert "Please make sure to" in report


def test_generate_report_flags_low_engagement_zones():
    report = generate_report(AUDIT_FINDINGS, FREQ_TABLE, ZONE_STATS)
    assert "context" in report
    assert "constraints" in report


def test_generate_report_handles_empty_inputs():
    report = generate_report([], {}, {})
    assert isinstance(report, str)
    assert len(report) > 0
