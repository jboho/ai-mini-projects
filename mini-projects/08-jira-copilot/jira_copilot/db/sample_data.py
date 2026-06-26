"""Synthetic TAWOS-like sample data for development and tests.

Lets the whole system run without the real MySQL dump. convert_tawos.py --sample
and the test fixtures both build from here.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from .models import Comment, Component, Issue, IssueLink, Project, Sprint, User

_DAY = datetime.timedelta(days=1)
_BASE = datetime.datetime(2023, 1, 1)


def build_sample(session: Session) -> None:
    project = Project(key="APACHE", name="Apache Demo")
    session.add(project)
    session.flush()

    users = [User(username=u, display_name=u.title()) for u in ("alice", "bob", "carol")]
    components = [Component(project_id=project.id, name=n) for n in ("api", "ui", "storage")]
    sprints = [
        Sprint(
            project_id=project.id, name="Sprint 1", state="closed", completed_date=_BASE + 14 * _DAY
        ),
        Sprint(project_id=project.id, name="Sprint 2", state="active"),
    ]
    session.add_all(users + components + sprints)
    session.flush()

    specs = [
        (
            "APACHE-1",
            "Bug",
            "Closed",
            "Critical",
            "App crashes on startup",
            "Null pointer when config missing",
            5,
            0,
            0,
            0,
        ),
        (
            "APACHE-2",
            "Bug",
            "Closed",
            "Major",
            "Slow query on dashboard",
            "Dashboard takes 10s to load",
            3,
            1,
            0,
            0,
        ),
        (
            "APACHE-3",
            "Story",
            "In Progress",
            "Major",
            "Add OAuth login",
            "Support Google and GitHub OAuth",
            8,
            2,
            1,
            1,
        ),
        (
            "APACHE-4",
            "Task",
            "Open",
            "Minor",
            "Update API docs",
            "Document the new endpoints",
            2,
            0,
            None,
            2,
        ),
        (
            "APACHE-5",
            "Bug",
            "Open",
            "Critical",
            "Data loss on sync",
            "Cart not syncing across devices",
            5,
            1,
            None,
            2,
        ),
        (
            "APACHE-6",
            "Story",
            "Closed",
            "Major",
            "Dark mode support",
            "Add a dark theme to the UI",
            5,
            2,
            0,
            1,
        ),
    ]
    issues = []
    for key, typ, status, prio, title, desc, pts, assignee_idx, sprint_idx, comp_idx in specs:
        issue = Issue(
            issue_key=key,
            project_id=project.id,
            type=typ,
            status=status,
            priority=prio,
            title=title,
            description_text=desc,
            story_points=pts,
            assignee_id=users[assignee_idx].id,
            sprint_id=sprints[sprint_idx].id if sprint_idx is not None else None,
            created=_BASE,
            resolved=_BASE + 7 * _DAY if status == "Closed" else None,
        )
        issue.components = [components[comp_idx]]
        issues.append(issue)
    session.add_all(issues)
    session.flush()

    session.add_all(
        [
            Comment(
                issue_id=issues[0].id,
                author_id=users[1].id,
                body="Confirmed on v2.1",
                created=_BASE,
            ),
            Comment(
                issue_id=issues[4].id,
                author_id=users[0].id,
                body="High impact, many reports",
                created=_BASE,
            ),
            IssueLink(
                source_issue_id=issues[4].id, target_issue_id=issues[1].id, link_type="relates to"
            ),
            IssueLink(
                source_issue_id=issues[2].id, target_issue_id=issues[3].id, link_type="blocks"
            ),
        ]
    )
    session.flush()
