from collections import Counter


def _executive_summary(audit_findings: list[dict]) -> list[str]:
    lines = ["## Executive Summary", ""]
    high_conf = [f for f in audit_findings if f.get("confidence") == "high"]
    if high_conf:
        cats = Counter(f["category"] for f in high_conf)
        for cat, count in cats.most_common(3):
            lines.append(f"- **{cat}**: {count} high-confidence finding(s)")
    else:
        lines.append("- No high-confidence findings.")
    return lines + [""]


def _rewrite_examples(audit_findings: list[dict]) -> list[str]:
    lines = ["## Rewrite Examples (Pass 1: LLM Audit)", ""]
    visible = [f for f in audit_findings if f.get("confidence") in ("high", "medium")]
    if visible:
        for f in visible:
            lines += [
                f"**Category:** {f['category']} | **Confidence:** {f['confidence']}",
                f"**Remove/rewrite:** `{f['excerpt']}`",
                f"**Suggestion:** {f['suggestion']}",
                "**Review:** `[ ] Valid`  `[ ] Disagree`",
                "",
            ]
    else:
        lines += ["No high- or medium-confidence rewrite examples found.", ""]
    return lines


def _frequency_table(freq_table: dict) -> list[str]:
    lines = ["## Frequency Breakdown (Pass 2: Statistical)", ""]
    if freq_table:
        lines += ["| Pattern | Count | % of Prompts |", "|---------|-------|-------------|"]
        for pattern, data in sorted(freq_table.items(), key=lambda x: -x[1]["percentage"]):
            lines.append(f"| `{pattern}` | {data['count']} | {data['percentage']}% |")
    else:
        lines.append("No filler patterns found to measure.")
    return lines + [""]


def _zone_table(zone_stats: dict[str, float]) -> list[str]:
    lines = ["## Structural Dead Weight (Pass 3: Zone Analysis)", ""]
    if zone_stats:
        lines += ["| Zone | Avg Engagement | Note |", "|------|---------------|------|"]
        for zone, score in sorted(zone_stats.items(), key=lambda x: x[1]):
            note = "low — consider removing" if score < 0.20 else ""
            lines.append(f"| {zone} | {score:.2f} | {note} |")
    else:
        lines.append("No structural analysis data.")
    return lines + [""]


def _appendix(audit_findings: list[dict]) -> list[str]:
    low_conf = [f for f in audit_findings if f.get("confidence") == "low"]
    if not low_conf:
        return []
    lines = ["## Appendix: Low-Confidence Findings", ""]
    for f in low_conf:
        lines.append(f"- [{f['category']}] `{f['excerpt']}` — {f['suggestion']}")
    return lines + [""]


def generate_report(
    audit_findings: list[dict],
    freq_table: dict,
    zone_stats: dict[str, float],
) -> str:
    sections = (
        ["# Prompt Optimizer Report", ""]
        + _executive_summary(audit_findings)
        + _rewrite_examples(audit_findings)
        + _frequency_table(freq_table)
        + _zone_table(zone_stats)
        + _appendix(audit_findings)
    )
    return "\n".join(sections)
