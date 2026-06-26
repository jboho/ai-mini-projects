"""Phase 3: error / stack-trace extraction."""

from __future__ import annotations

from pipeline.services.text_analysis import (
    analyze_description,
    extract_errors,
    extract_stack_traces,
    profile_error_frequency,
)


def test_extract_java_exception_with_message():
    errors = extract_errors("java.lang.OutOfMemoryError: Java heap space")
    assert errors == ["OutOfMemoryError: Java heap space"]


def test_extract_multiple_and_dedup():
    text = "NullPointerException here\nNullPointerException there\nIOException: disk"
    errors = extract_errors(text)
    assert "NullPointerException" in errors
    assert "IOException: disk" in errors
    assert errors.count("NullPointerException") == 1


def test_extract_stack_trace_block():
    text = (
        "java.lang.OutOfMemoryError: Java heap space\n"
        "\tat org.apache.spark.executor.Executor.run(Executor.java:142)\n"
        "\tat org.apache.spark.shuffle.Reader.read(Reader.scala:88)"
    )
    traces = extract_stack_traces(text)
    assert len(traces) == 1
    assert "Executor.run" in traces[0] and "Reader.read" in traces[0]


def test_python_traceback():
    text = "Traceback (most recent call last):\n  File x\nValueError: bad"
    traces = extract_stack_traces(text)
    assert traces and "ValueError" in traces[0]


def test_analyze_description_flags():
    result = analyze_description(
        "java.lang.OutOfMemoryError: Java heap space\n\tat Foo.bar(Foo.java:1)"
    )
    assert result.has_error and result.has_stacktrace
    assert "OutOfMemoryError" in result.keywords


def test_no_error_text():
    result = analyze_description("everything is fine, no problems at all")
    assert not result.has_error and result.errors == []


def test_profile_error_frequency(session):
    freq = profile_error_frequency(session, "SPARK")
    assert freq.get("OutOfMemoryError", 0) >= 1
