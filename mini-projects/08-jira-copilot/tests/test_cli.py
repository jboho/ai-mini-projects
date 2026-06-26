"""CLI tests via Typer's CliRunner with an injected in-memory runtime."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from jira_copilot.agents.crew import JiraCopilotCrew
from jira_copilot.cli import commands
from jira_copilot.cli.commands import Runtime, app
from jira_copilot.services.analytics import Analytics
from jira_copilot.services.issue_writer import IssueWriter


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def rt(session, vector_store, monkeypatch):
    crew = JiraCopilotCrew(session, vector_store)
    runtime = Runtime(
        session=session,
        store=vector_store,
        crew=crew,
        writer=IssueWriter(session),
        analytics=Analytics(session),
    )
    monkeypatch.setattr(commands, "build_runtime", lambda: runtime)
    return runtime


def test_search(runner, rt):
    result = runner.invoke(app, ["search", "oauth login"])
    assert result.exit_code == 0
    assert "APACHE-3" in result.stdout


def test_query(runner, rt):
    result = runner.invoke(app, ["query", "find open bugs in APACHE"])
    assert result.exit_code == 0
    assert "intent=search" in result.stdout


def test_context(runner, rt):
    result = runner.invoke(app, ["context", "APACHE-4"])
    assert result.exit_code == 0
    assert "storage" in result.stdout
    assert "APACHE-3" in result.stdout


def test_suggest_priority(runner, rt):
    result = runner.invoke(app, ["suggest", "APACHE-5", "--type", "priority"])
    assert result.exit_code == 0
    assert "Critical" in result.stdout


def test_plan_sprint(runner, rt):
    result = runner.invoke(app, ["plan-sprint", "APACHE"])
    assert result.exit_code == 0
    assert "capacity=13" in result.stdout
    assert "APACHE-5" in result.stdout


def test_velocity(runner, rt):
    result = runner.invoke(app, ["velocity", "APACHE"])
    assert result.exit_code == 0
    assert "13" in result.stdout


def test_release_notes(runner, rt):
    result = runner.invoke(app, ["release-notes", "1"])
    assert result.exit_code == 0
    assert "Bug Fixes" in result.stdout


def test_chat_one_shot(runner, rt):
    result = runner.invoke(app, ["chat", "find issues about oauth login"])
    assert result.exit_code == 0
    assert "intent=" in result.stdout


def test_pending_and_execute(runner, rt):
    op = rt.writer.simulate_update("APACHE-4", "priority", "Critical")
    rt.session.commit()

    listed = runner.invoke(app, ["pending"])
    assert f"#{op.id}" in listed.stdout

    done = runner.invoke(app, ["execute", str(op.id)])
    assert done.exit_code == 0
    assert "Executed 1" in done.stdout
    from jira_copilot.services.issue_service import IssueService

    assert IssueService(rt.session).get_issue("APACHE-4").priority == "Critical"


def test_stats(runner, rt):
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "total_suggestions" in result.stdout
