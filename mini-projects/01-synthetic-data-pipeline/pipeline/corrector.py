"""Phase 5: Corrected prompt templates with documented rationale.

Each correction targets specific failure modes identified by baseline analysis.
Every change is documented with: what changed, which failure mode it addresses,
which template(s) it affects, and why.
"""

from __future__ import annotations

from .models import RepairCategory

# ── Correction Documentation ────────────────────────────────────────
#
# The corrections below are additive paragraphs appended to each baseline
# prompt. They target the 6 failure modes without rewriting the original
# persona or category framing.
#
# CHANGE LOG (one entry per correction):
#
# 1. incomplete_answer (all templates)
#    Change: Added "Your answer MUST contain at least 5 numbered steps,
#            each specific enough that a first-time DIYer could follow
#            without guessing."
#    Reason: Baseline items often had vague or too-few steps.
#
# 2. safety_violations (all templates, especially electrical & HVAC)
#    Change: Added "You MUST include at least one specific safety
#            precaution relevant to the task. For electrical work,
#            always mention turning off the breaker AND testing with a
#            voltage tester. For plumbing, always mention shutting off
#            the water supply valve."
#    Reason: Baseline safety_violations rate was the most common failure
#            mode. Many items had no actionable safety warning.
#
# 3. unrealistic_tools (all templates)
#    Change: Added "Tools must be limited to items found in a basic
#            home toolkit: screwdrivers, adjustable wrench, pliers,
#            tape measure, utility knife, plumber's tape, flashlight,
#            bucket, rags, level, hammer, drill. Do NOT list
#            professional-grade tools."
#    Reason: Generator sometimes listed specialty tools (e.g. pipe
#            threader, refrigerant gauge) that homeowners wouldn't own.
#
# 4. overcomplicated_solution (all templates)
#    Change: Added "This is a DIY task. Do NOT recommend hiring a
#            professional unless there is genuine danger (e.g. main
#            electrical panel, gas line work). The solution should be
#            achievable by someone with no prior repair experience."
#    Reason: Some items defaulted to "call a professional" for tasks
#            like replacing a light switch or fixing a running toilet.
#
# 5. missing_context (all templates)
#    Change: Added "The question must name the specific appliance,
#            fixture, or area (e.g. 'kitchen faucet', 'bathroom
#            exhaust fan', 'bedroom drywall'). The answer must
#            reference the same specific item. Do not use generic
#            terms like 'the unit' or 'the thing'."
#    Reason: Vague questions and answers that didn't specify what
#            fixture or appliance was being repaired.
#
# 6. poor_quality_tips (all templates)
#    Change: Added "Each tip must be a specific, actionable piece of
#            advice — NOT generic platitudes like 'be careful' or
#            'take your time'. Example of a good tip: 'Apply plumber's
#            tape clockwise when wrapping threads to ensure it doesn't
#            unravel when tightening.'"
#    Reason: Tips were often vague filler text with no practical value.
#
# ─────────────────────────────────────────────────────────────────────

_CORRECTION_SUFFIX = """

CRITICAL QUALITY REQUIREMENTS — you must satisfy ALL of these:

1. COMPLETENESS: Your answer MUST contain at least 5 numbered steps, each
   specific enough that a first-time DIYer could follow without guessing.
   Never skip a step because it seems obvious.

2. SAFETY: You MUST include at least one specific, actionable safety
   precaution directly relevant to THIS task. For electrical work, always
   mention turning off the breaker AND verifying with a non-contact voltage
   tester. For plumbing, always mention shutting off the water supply valve.
   For anything involving chemicals, mention ventilation and protective gear.

3. REALISTIC TOOLS: Tools must be limited to items found in a basic home
   toolkit: screwdrivers (Phillips and flathead), adjustable wrench, pliers,
   tape measure, utility knife, plumber's tape, flashlight, bucket, rags,
   level, hammer, cordless drill. Do NOT list professional-grade or
   specialty tools.

4. DIY APPROPRIATE: This is a DIY task for a homeowner. Do NOT recommend
   hiring a professional unless there is genuine danger (main electrical
   panel, gas line work, structural load-bearing changes). The solution
   should be achievable by someone with no prior repair experience.

5. SPECIFIC CONTEXT: The question must name the specific appliance, fixture,
   or area of the home (e.g. "kitchen faucet", "bathroom exhaust fan",
   "bedroom drywall"). The answer must reference the same specific item
   throughout. Never use generic terms like "the unit" or "the thing".

6. ACTIONABLE TIPS: Each tip must be a specific, actionable piece of advice.
   NOT generic platitudes like "be careful" or "take your time". Example of
   a good tip: "Apply plumber's tape clockwise when wrapping threads to
   ensure it doesn't unravel when you tighten the fitting."
"""

# Baseline prompts imported at function call time to avoid circular imports
_CORRECTED: dict[RepairCategory, str] | None = None


def get_corrected_prompts() -> dict[RepairCategory, str]:
    """Return corrected prompts: baseline + correction suffix per category."""
    global _CORRECTED
    if _CORRECTED is not None:
        return _CORRECTED

    from .generator import BASELINE_PROMPTS

    _CORRECTED = {
        cat: base + _CORRECTION_SUFFIX
        for cat, base in BASELINE_PROMPTS.items()
    }
    return _CORRECTED


CORRECTION_LOG: list[dict[str, str]] = [
    {
        "change": "Added 'at least 5 numbered steps, each specific enough for a first-timer'",
        "failure_mode": "incomplete_answer",
        "templates": "all",
        "reason": "Baseline items frequently had vague or too-few steps to complete the repair.",
    },
    {
        "change": "Added explicit safety precaution requirements per task type",
        "failure_mode": "safety_violations",
        "templates": "all (especially electrical, HVAC)",
        "reason": "safety_violations was the most common failure mode; many items lacked actionable safety warnings.",
    },
    {
        "change": "Added explicit whitelist of allowed household tools",
        "failure_mode": "unrealistic_tools",
        "templates": "all",
        "reason": "Generator listed specialty tools (pipe threader, refrigerant gauge) homeowners don't own.",
    },
    {
        "change": "Added 'Do NOT recommend hiring a professional unless genuine danger'",
        "failure_mode": "overcomplicated_solution",
        "templates": "all",
        "reason": "Some items defaulted to 'call a pro' for tasks like replacing a light switch.",
    },
    {
        "change": "Added 'question must name the specific appliance/fixture/area'",
        "failure_mode": "missing_context",
        "templates": "all",
        "reason": "Vague questions using generic terms like 'the unit' or 'the thing'.",
    },
    {
        "change": "Added 'each tip must be specific and actionable, not platitudes'",
        "failure_mode": "poor_quality_tips",
        "templates": "all",
        "reason": "Tips were often vague filler text ('be careful', 'take your time').",
    },
]
