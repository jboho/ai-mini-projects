"""Phase 3: LLM-as-Judge — evaluate each Q&A item for 6 failure modes."""

from __future__ import annotations

import logging
import time

from .client import get_instructor_client, get_model_name
from .models import DIYRepairItem, JudgeResult, PipelineRecord

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """\
You are an expert quality evaluator for DIY home repair guidance. Your job is
to independently assess whether a generated Q&A item meets quality standards
across 6 failure dimensions.

For each dimension, output 0 (pass) or 1 (fail).

## Failure Modes

1. **incomplete_answer** — The answer lacks enough detail to actually complete
   the repair. A homeowner following only these instructions would get stuck.
   Example FAIL: "Replace the part and reassemble." (no specifics on which
   part, how to access it, or how to reassemble)
   Example PASS: Numbered steps that walk through disassembly, part
   replacement, and reassembly with enough detail to follow.

2. **safety_violations** — Missing or incorrect safety warnings for a task
   that has real hazards. Electrical work without "turn off the breaker",
   plumbing without "shut off the water supply", or any task with chemical
   or physical hazards that lacks warnings.
   Example FAIL: Electrical outlet replacement with no mention of turning
   off power or testing for voltage.
   Example PASS: "Turn off the circuit breaker. Use a non-contact voltage
   tester to confirm the outlet is dead before touching any wires."

3. **unrealistic_tools** — Requires professional or specialized tools that a
   typical homeowner would not own: pipe threaders, refrigerant gauges,
   oscilloscopes, conduit benders, torque wrenches, etc.
   Example FAIL: tools_required includes "refrigerant recovery machine".
   Example PASS: tools_required lists adjustable wrench, screwdriver,
   plumber's tape — items found in a basic home toolkit.

4. **overcomplicated_solution** — Recommends calling a professional or
   describes a process far too complex for a straightforward DIY task. The
   solution should match the difficulty of the problem.
   Example FAIL: Suggests hiring an electrician to replace a light switch.
   Example PASS: Provides clear DIY steps for replacing a light switch.

5. **missing_context** — The question or answer lacks enough context to
   understand the problem. The equipment/situation is unclear, or the answer
   doesn't specify which type of fixture, appliance, or component it applies to.
   Example FAIL: "Fix the thing that's leaking." (what thing? where?)
   Example PASS: "Kitchen faucet with dripping water from the spout."

6. **poor_quality_tips** — Tips are vague, generic, or unhelpful. Platitudes
   like "be careful", "take your time", or "good luck" do not count as real tips.
   Example FAIL: tips = ["Be careful", "Good luck!"]
   Example PASS: tips = ["Apply plumber's tape clockwise to ensure a tight seal."]
"""

CALL_DELAY = 0.3


def judge_item(item: DIYRepairItem) -> JudgeResult:
    """Evaluate a single DIY repair item against all 6 failure modes."""
    client = get_instructor_client()
    model = get_model_name()

    item_text = (
        f"Question: {item.question}\n"
        f"Answer: {item.answer}\n"
        f"Equipment/Problem: {item.equipment_problem}\n"
        f"Tools Required: {', '.join(item.tools_required)}\n"
        f"Steps:\n"
        + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(item.steps))
        + f"\nSafety Info: {item.safety_info}\n"
        f"Tips: {', '.join(item.tips)}"
    )

    result: JudgeResult = client.chat.completions.create(
        model=model,
        response_model=JudgeResult,
        max_retries=2,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Evaluate the following DIY repair Q&A item. "
                    "For each of the 6 failure modes, output 0 (pass) or "
                    "1 (fail).\n\n" + item_text
                ),
            },
        ],
        temperature=0,
    )
    return result


def judge_records(records: list[PipelineRecord]) -> list[PipelineRecord]:
    """Run the LLM judge on every validated record in the list.

    Records that failed validation (item is None) are skipped.
    """
    judged = 0
    failed = 0

    for record in records:
        if record.item is None:
            continue

        try:
            result = judge_item(record.item)
            record.judge_result = result
            record.metadata.judge_result = result
            judged += 1

            if result.overall_failure:
                failed += 1

            logger.info(
                "Judged %s: %d failures %s",
                record.trace_id,
                result.failure_count,
                result.model_dump(),
            )
        except Exception as exc:
            logger.error(
                "Judge failed for %s: %s", record.trace_id, exc
            )

        if CALL_DELAY > 0:
            time.sleep(CALL_DELAY)

    rate = (failed / judged * 100) if judged else 0
    logger.info(
        "Judge complete: %d/%d items failed (%.1f%%)",
        failed, judged, rate,
    )

    return records
