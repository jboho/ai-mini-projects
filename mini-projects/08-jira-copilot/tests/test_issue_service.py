"""Tests for the IssueService data access layer."""

from __future__ import annotations

from jira_copilot.services.issue_service import IssueService


def test_get_issue(session):
    svc = IssueService(session)
    issue = svc.get_issue("APACHE-1")
    assert issue is not None
    assert issue.title == "App crashes on startup"
    assert svc.get_issue("NOPE-999") is None


def test_search_issues_filters(session):
    svc = IssueService(session)
    bugs = svc.search_issues(type="Bug")
    assert len(bugs) == 3
    open_critical = svc.search_issues(status="Open", priority="Critical")
    assert all(i.status == "Open" and i.priority == "Critical" for i in open_critical)
    assert svc.search_issues(project_key="APACHE")  # project filter resolves


def test_linked_issues(session):
    svc = IssueService(session)
    links = svc.get_linked_issues("APACHE-5")
    assert any(other.issue_key == "APACHE-2" and lt == "relates to" for other, lt in links)


def test_comments(session):
    svc = IssueService(session)
    comments = svc.get_issue_comments("APACHE-1")
    assert len(comments) == 1 and "Confirmed" in comments[0].body


def test_components(session):
    svc = IssueService(session)
    names = {c.name for c in svc.get_project_components("APACHE")}
    assert {"api", "ui", "storage"} <= names


def test_velocity(session):
    svc = IssueService(session)
    velocity = svc.get_project_velocity("APACHE", n_sprints=5)
    assert len(velocity) == 1  # one closed sprint
    # Sprint 1 closed issues: APACHE-1 (5) + APACHE-2 (3) + APACHE-6 (5) = 13 points
    assert velocity[0]["completed_points"] == 13
