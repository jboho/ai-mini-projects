"""Phase 1: Generate diverse DIY repair Q&A items via LLM."""

from __future__ import annotations

import logging
import random
import time

import instructor

from .client import get_instructor_client, get_model_name
from .models import DIYRepairItem, RepairCategory

logger = logging.getLogger(__name__)

BASELINE_PROMPTS: dict[RepairCategory, str] = {
    RepairCategory.APPLIANCE: (
        "You are a seasoned home appliance repair technician with 20 years of "
        "experience fixing refrigerators, washing machines, dryers, dishwashers, "
        "and ovens. A homeowner asks you for help with a common appliance problem. "
        "Generate a realistic Q&A pair. The question should sound like a real "
        "homeowner describing their problem. The answer must include clear "
        "step-by-step instructions using only tools a typical homeowner would own. "
        "Include safety precautions and practical tips."
    ),
    RepairCategory.PLUMBING: (
        "You are a licensed plumber who specializes in residential plumbing. "
        "You help homeowners fix leaks, clogs, fixture problems, and pipe issues "
        "without calling a professional. Generate a realistic Q&A pair about a "
        "common plumbing problem. The question should come from a homeowner who "
        "is not a plumber. The answer must provide numbered repair steps, list "
        "only standard household tools, and include water safety warnings."
    ),
    RepairCategory.ELECTRICAL: (
        "You are a certified electrician who teaches homeowners safe, code-compliant "
        "electrical work they can do themselves: outlet replacement, light switch "
        "repair, fixture installation, and similar tasks. Generate a realistic Q&A "
        "pair about a safe homeowner-level electrical repair. The question should "
        "describe a specific symptom. The answer must emphasize turning off the "
        "breaker, testing for voltage, and include detailed safety warnings."
    ),
    RepairCategory.HVAC: (
        "You are an HVAC maintenance specialist who helps homeowners with filter "
        "changes, thermostat troubleshooting, vent cleaning, and basic system "
        "maintenance. Generate a realistic Q&A pair about a common HVAC maintenance "
        "task. The question should describe a comfort or performance issue. The "
        "answer must include specific steps, mention only standard tools, and warn "
        "about any safety concerns like gas or refrigerant."
    ),
    RepairCategory.GENERAL: (
        "You are an experienced general contractor who helps homeowners with "
        "drywall repair, door and window fixes, flooring issues, and basic "
        "carpentry. Generate a realistic Q&A pair about a common home repair "
        "task. The question should describe visible damage or a functional "
        "problem. The answer must list tools, provide numbered steps, and "
        "include tips for a clean professional-looking result."
    ),
}

CORRECTED_PROMPTS: dict[RepairCategory, str] = {}

MAX_RETRIES = 3
RETRY_DELAY_BASE = 2.0
CALL_DELAY = 0.5


def generate_items(
    num_items: int = 50,
    *,
    prompts: dict[RepairCategory, str] | None = None,
    prompt_version: str = "baseline",
) -> list[tuple[DIYRepairItem | None, RepairCategory, list[str]]]:
    """Generate *num_items* DIY repair Q&A items.

    Returns a list of (item_or_None, category, validation_errors) tuples.
    """
    if prompts is None:
        prompts = BASELINE_PROMPTS

    client = get_instructor_client()
    model = get_model_name()
    categories = list(RepairCategory)
    results: list[tuple[DIYRepairItem | None, RepairCategory, list[str]]] = []

    for i in range(num_items):
        category = random.choice(categories)
        system_prompt = prompts[category]
        item: DIYRepairItem | None = None
        errors: list[str] = []

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                item = client.chat.completions.create(
                    model=model,
                    response_model=DIYRepairItem,
                    max_retries=2,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": (
                                "Generate one DIY repair Q&A item now. "
                                "Return all 7 fields."
                            ),
                        },
                    ],
                    temperature=0.9,
                )
                break
            except instructor.exceptions.InstructorRetryException as exc:
                errors.append(f"attempt {attempt}: {exc}")
                logger.warning(
                    "Retry exhausted for item %d attempt %d: %s",
                    i + 1, attempt, exc,
                )
            except Exception as exc:
                errors.append(f"attempt {attempt}: {exc}")
                logger.warning(
                    "Error generating item %d attempt %d: %s",
                    i + 1, attempt, exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_BASE * attempt)

        results.append((item, category, errors))
        logger.info(
            "Item %d/%d [%s] %s",
            i + 1,
            num_items,
            category.value,
            "OK" if item else f"FAILED ({len(errors)} errors)",
        )

        if CALL_DELAY > 0:
            time.sleep(CALL_DELAY)

    return results
