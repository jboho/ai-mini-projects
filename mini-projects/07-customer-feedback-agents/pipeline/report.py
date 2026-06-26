"""Markdown + HTML report generation from pipeline output."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from .config import DATA_DIR
from .orchestrator import PipelineOutput

_HTML = Template(
    """<!doctype html><html><head><meta charset="utf-8"><title>Feedback Report</title>
<style>body{font-family:system-ui;margin:2rem;max-width:60rem}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:.4rem .6rem}
th{background:#1f7a4d;color:#fff}.gap{background:#fdecea}</style></head><body>
<h1>Customer Feedback Analysis</h1>
<p>{{ n_feedback }} feedback items · {{ n_themes }} themes · {{ n_gaps }} gaps ·
sentiment accuracy {{ accuracy }}</p>
<h2>Top gaps by priority</h2>
<table><tr><th>Theme</th><th>Priority</th><th>Feedback</th><th>Avg pain</th><th>Covered</th><th>Recommendations</th></tr>
{% for g in gaps %}<tr class="{{ '' if g.has_coverage else 'gap' }}">
<td>{{ g.theme_name }}</td><td>{{ '%.2f'|format(g.priority_score) }}</td><td>{{ g.feedback_count }}</td>
<td>{{ '%.2f'|format(g.avg_pain) }}</td><td>{{ 'yes' if g.has_coverage else 'NO' }}</td>
<td>{{ g.recommendations|join('; ') }}</td></tr>{% endfor %}
</table></body></html>"""
)


def render_markdown(output: PipelineOutput) -> str:
    acc = output.evaluation.get("sentiment_accuracy", {}).get("overall", "n/a")
    lines = [
        "# Customer Feedback Analysis",
        "",
        f"- Feedback analyzed: **{len(output.feedback)}**",
        f"- Themes: **{len(output.themes)}**",
        f"- Gaps (uncovered themes): **{sum(1 for g in output.gaps if not g.has_coverage)}**",
        f"- Sentiment accuracy vs stars: **{acc}**",
        "",
        "## Top gaps by priority",
        "",
        "| Theme | Priority | Feedback | Avg pain | Covered | Recommendations |",
        "|-------|----------|----------|----------|---------|-----------------|",
    ]
    for g in output.gaps:
        lines.append(
            f"| {g.theme_name} | {g.priority_score:.2f} | {g.feedback_count} | "
            f"{g.avg_pain:.2f} | {'yes' if g.has_coverage else 'NO'} | "
            f"{'; '.join(g.recommendations)} |"
        )
    return "\n".join(lines)


def generate_reports(
    output: PipelineOutput, directory: str | Path | None = None
) -> tuple[Path, Path]:
    directory = Path(directory) if directory else DATA_DIR
    directory.mkdir(parents=True, exist_ok=True)
    md_path = directory / "report.md"
    md_path.write_text(render_markdown(output))
    html_path = directory / "report.html"
    html_path.write_text(
        _HTML.render(
            n_feedback=len(output.feedback),
            n_themes=len(output.themes),
            n_gaps=sum(1 for g in output.gaps if not g.has_coverage),
            accuracy=output.evaluation.get("sentiment_accuracy", {}).get("overall", "n/a"),
            gaps=output.gaps,
        )
    )
    return md_path, html_path
