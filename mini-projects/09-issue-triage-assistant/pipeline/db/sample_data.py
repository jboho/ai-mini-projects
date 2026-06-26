"""Synthetic, triage-shaped sample data so the whole system runs without the 1.7GB CSV.

Generates issues across the target projects covering all 13 categories, with:
- true duplicates that normalize to the same error signature (SPARK-1001/1002/FLINK-2001),
- resolved issues carrying a fix comment (so learn_from_resolved has material),
- comments, status transitions, and issue links.

``run_pipeline.py --mode ingest`` (sample) and the test fixtures both build from here.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from .tables import IssueComment, IssueLink, JiraIssue, StatusTransition

_DAY = datetime.timedelta(days=1)
_BASE = datetime.datetime(2024, 1, 1)

# The same OutOfMemoryError, reported three times with different line numbers and
# timestamps. After normalization these collapse to one signature -> recurring bug.
_OOM_DESC_A = (
    "2024-01-03 10:22:41 Executor crashed during shuffle read.\n"
    "java.lang.OutOfMemoryError: Java heap space\n"
    "\tat org.apache.spark.executor.Executor.run(Executor.java:142)\n"
    "\tat org.apache.spark.shuffle.BlockStoreShuffleReader.read(BlockStoreShuffleReader.scala:88)"
)
_OOM_DESC_B = (
    "2024-01-05 23:11:07 Executor crashed during shuffle read.\n"
    "java.lang.OutOfMemoryError: Java heap space\n"
    "\tat org.apache.spark.executor.Executor.run(Executor.java:377)\n"
    "\tat org.apache.spark.shuffle.BlockStoreShuffleReader.read(BlockStoreShuffleReader.scala:213)"
)


def _issue(session: Session, **kw) -> JiraIssue:
    issue = JiraIssue(**kw)
    session.add(issue)
    return issue


def build_sample(session: Session) -> None:
    issues: list[tuple] = [
        # key, project, summary, description, type, priority, status, resolution, created_off, resolved_off
        (
            "SPARK-1001",
            "SPARK",
            "Executor fails with OutOfMemoryError: Java heap space during shuffle",
            _OOM_DESC_A,
            "Bug",
            "Critical",
            "Open",
            "",
            2,
            None,
        ),
        (
            "SPARK-1002",
            "SPARK",
            "Executor fails with OutOfMemoryError: Java heap space during shuffle",
            _OOM_DESC_B,
            "Bug",
            "Critical",
            "Open",
            "",
            4,
            None,
        ),
        (
            "FLINK-2001",
            "FLINK",
            "Executor fails with OutOfMemoryError: Java heap space during shuffle",
            _OOM_DESC_A,
            "Bug",
            "Major",
            "Open",
            "",
            6,
            None,
        ),
        (
            "HADOOP-3001",
            "HADOOP",
            "NullPointerException when parsing malformed record",
            "Reducer throws java.lang.NullPointerException on null key.\n"
            "\tat org.apache.hadoop.mapred.ReduceTask.run(ReduceTask.java:401)",
            "Bug",
            "Major",
            "Open",
            "",
            3,
            None,
        ),
        (
            "KAFKA-4001",
            "KAFKA",
            "Producer fails with SocketTimeoutException to broker",
            "Connection to broker times out under load.\n"
            "java.net.SocketTimeoutException: Read timed out",
            "Bug",
            "Major",
            "Resolved",
            "Fixed",
            5,
            12,
        ),
        (
            "HDFS-5001",
            "HDFS",
            "DataNode write fails: No space left on device",
            "java.io.IOException: No space left on device while writing block.",
            "Bug",
            "Critical",
            "Open",
            "",
            7,
            None,
        ),
        (
            "HIVE-6001",
            "HIVE",
            "Deadlock between compaction threads",
            "Two compaction threads deadlock acquiring table locks in reverse order.",
            "Bug",
            "Major",
            "Open",
            "",
            8,
            None,
        ),
        (
            "CASSANDRA-7001",
            "CASSANDRA",
            "Startup fails with ClassNotFoundException for snappy",
            "java.lang.ClassNotFoundException: org.xerial.snappy.Snappy on classpath.",
            "Bug",
            "Major",
            "Resolved",
            "Fixed",
            9,
            15,
        ),
        (
            "HBASE-8001",
            "HBASE",
            "RegionServer aborts due to misconfigured zookeeper quorum",
            "ConfigException: hbase.zookeeper.quorum property not set correctly.",
            "Bug",
            "Major",
            "Open",
            "",
            10,
            None,
        ),
        (
            "ZOOKEEPER-9001",
            "ZOOKEEPER",
            "AuthenticationException with Kerberos enabled",
            "javax.security.sasl.AuthenticationException: GSS initiate failed (permission denied).",
            "Bug",
            "Critical",
            "Resolved",
            "Fixed",
            6,
            14,
        ),
        (
            "YARN-1101",
            "YARN",
            "NotSerializableException when checkpointing state",
            "java.io.NotSerializableException: com.example.UserState during kryo serialization.",
            "Bug",
            "Major",
            "Open",
            "",
            11,
            None,
        ),
        (
            "SPARK-1003",
            "SPARK",
            "Slow query: aggregation took 45000 ms",
            "Performance regression: a simple aggregation slow query took 45000 ms after upgrade.",
            "Improvement",
            "Minor",
            "Resolved",
            "Fixed",
            4,
            18,
        ),
        (
            "HADOOP-3002",
            "HADOOP",
            "BUILD FAILURE: cannot find symbol in MapTask",
            "compilation failed: BUILD FAILURE, cannot find symbol method getProgress().",
            "Bug",
            "Minor",
            "Open",
            "",
            12,
            None,
        ),
        (
            "FLINK-2002",
            "FLINK",
            "Deprecated API: TableEnvironment.sqlUpdate removed",
            "Job uses deprecated API removed in 1.17; UnsupportedOperationException at runtime.",
            "Bug",
            "Minor",
            "Open",
            "",
            13,
            None,
        ),
    ]

    by_key: dict[str, JiraIssue] = {}
    for key, proj, summary, desc, typ, prio, status, res, c_off, r_off in issues:
        issue = _issue(
            session,
            key=key,
            project_key=proj,
            summary=summary,
            description=desc,
            issuetype=typ,
            priority=prio,
            status=status,
            resolution=res,
            components="core",
            created_at=_BASE + c_off * _DAY,
            resolved_at=_BASE + r_off * _DAY if r_off is not None else None,
        )
        by_key[key] = issue
    session.flush()

    # Fix comments on the resolved issues (material for learn_from_resolved).
    fixes = {
        "KAFKA-4001": "Fixed by raising request.timeout.ms and adding retry backoff. Committed in a1b2c3.",
        "CASSANDRA-7001": "Resolved: added snappy-java to the runtime classpath. See commit d4e5f6.",
        "ZOOKEEPER-9001": "Fixed by correcting the Kerberos principal and keytab permissions.",
        "SPARK-1003": "Resolution: added a broadcast join hint and cached the dimension table.",
    }
    for key, body in fixes.items():
        session.add(
            IssueComment(
                issue_key=key,
                author="committer",
                body=body,
                created_at=_BASE + 16 * _DAY,
                contains_error=False,
                contains_stacktrace=False,
                contains_fix=True,
            )
        )

    # A diagnostic comment with a stack trace (for text analysis).
    session.add(
        IssueComment(
            issue_key="SPARK-1001",
            author="reporter",
            body="Reproduced again:\njava.lang.OutOfMemoryError: Java heap space\n"
            "\tat org.apache.spark.executor.Executor.run(Executor.java:142)",
            created_at=_BASE + 3 * _DAY,
            contains_error=True,
            contains_stacktrace=True,
            contains_fix=False,
        )
    )

    # Status transitions for the resolved issues.
    for key in fixes:
        session.add(
            StatusTransition(
                issue_key=key,
                field="status",
                from_value="Open",
                to_value="Resolved",
                author="committer",
                created_at=_BASE + 16 * _DAY,
            )
        )

    # Links: the duplicates relate to each other; SPARK-1003 blocks SPARK-1001.
    session.add_all(
        [
            IssueLink(
                source_key="SPARK-1002",
                target_key="SPARK-1001",
                link_type="duplicates",
                target_status="Open",
            ),
            IssueLink(
                source_key="FLINK-2001",
                target_key="SPARK-1001",
                link_type="relates to",
                target_status="Open",
            ),
            IssueLink(
                source_key="SPARK-1003",
                target_key="SPARK-1001",
                link_type="blocks",
                target_status="Open",
            ),
        ]
    )
    session.flush()
