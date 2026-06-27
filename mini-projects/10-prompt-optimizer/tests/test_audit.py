import pytest
from unittest.mock import MagicMock, patch
from optimizer.audit import audit_pairs, CATEGORIES

SAMPLE_PAIRS = [
    {
        "prompt": "Please make sure to write clean code. I need you to implement a function that reads a file and returns its contents as a string.",
        "response": "Here is a function that reads a file:\n\ndef read_file(path):\n    with open(path) as f:\n        return f.read()",
    }
]

MOCK_RESPONSE_JSON = '{"findings": [{"category": "filler_phrase", "excerpt": "Please make sure to", "suggestion": "Remove — the model writes clean code by default.", "confidence": "high"}]}'


def test_audit_pairs_returns_list():
    with patch("optimizer.audit.anthropic.Anthropic") as MockClient:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=MOCK_RESPONSE_JSON)]
        MockClient.return_value.messages.create.return_value = mock_msg

        findings = audit_pairs(SAMPLE_PAIRS)

    assert isinstance(findings, list)
    assert len(findings) == 1


def test_audit_pairs_finding_has_required_keys():
    with patch("optimizer.audit.anthropic.Anthropic") as MockClient:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=MOCK_RESPONSE_JSON)]
        MockClient.return_value.messages.create.return_value = mock_msg

        findings = audit_pairs(SAMPLE_PAIRS)

    f = findings[0]
    assert "category" in f
    assert "excerpt" in f
    assert "suggestion" in f
    assert "confidence" in f
    assert "source_prompt" in f


def test_audit_pairs_category_is_valid():
    with patch("optimizer.audit.anthropic.Anthropic") as MockClient:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=MOCK_RESPONSE_JSON)]
        MockClient.return_value.messages.create.return_value = mock_msg

        findings = audit_pairs(SAMPLE_PAIRS)

    assert findings[0]["category"] in CATEGORIES


def test_audit_pairs_handles_malformed_json_gracefully():
    with patch("optimizer.audit.anthropic.Anthropic") as MockClient:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="not json at all")]
        MockClient.return_value.messages.create.return_value = mock_msg

        findings = audit_pairs(SAMPLE_PAIRS)

    assert findings == []


def test_audit_pairs_attaches_source_prompt():
    with patch("optimizer.audit.anthropic.Anthropic") as MockClient:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=MOCK_RESPONSE_JSON)]
        MockClient.return_value.messages.create.return_value = mock_msg

        findings = audit_pairs(SAMPLE_PAIRS)

    assert findings[0]["source_prompt"] == SAMPLE_PAIRS[0]["prompt"]
