from pathlib import Path
import pytest
from optimizer.loader import load_pairs_from_file, load_all_pairs

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_pairs_from_file_extracts_text_turns():
    pairs = load_pairs_from_file(FIXTURES / "sample.jsonl")
    assert len(pairs) == 2


def test_load_pairs_from_file_skips_tool_result_turns():
    pairs = load_pairs_from_file(FIXTURES / "sample.jsonl")
    for pair in pairs:
        assert "tool_result" not in pair["prompt"]


def test_load_pairs_from_file_skips_sidechain_messages(tmp_path):
    jl = tmp_path / "sc.jsonl"
    jl.write_text(
        '{"parentUuid":null,"isSidechain":true,"type":"user","message":{"role":"user","content":[{"type":"text","text":"this is a sidechain message that should be ignored entirely"}]},"uuid":"sc-1","sessionId":"s"}\n'
        '{"parentUuid":"sc-1","isSidechain":true,"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"sidechain response"}]},"uuid":"sc-2","sessionId":"s"}\n'
    )
    pairs = load_pairs_from_file(jl)
    assert pairs == []


def test_load_pairs_minimum_word_count(tmp_path):
    jl = tmp_path / "short.jsonl"
    jl.write_text(
        '{"parentUuid":null,"isSidechain":false,"type":"user","message":{"role":"user","content":[{"type":"text","text":"ok"}]},"uuid":"u1","sessionId":"s"}\n'
        '{"parentUuid":"u1","isSidechain":false,"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"done"}]},"uuid":"a1","sessionId":"s"}\n'
    )
    pairs = load_pairs_from_file(jl)
    assert pairs == []


def test_load_all_pairs_scans_directory(tmp_path):
    sub = tmp_path / "proj"
    sub.mkdir()
    import shutil
    shutil.copy(FIXTURES / "sample.jsonl", sub / "conv.jsonl")
    pairs = load_all_pairs(tmp_path)
    assert len(pairs) == 2


def test_load_all_pairs_returns_empty_for_missing_dir(tmp_path):
    pairs = load_all_pairs(tmp_path / "nonexistent")
    assert pairs == []
