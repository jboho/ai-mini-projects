"""Synthetic dating-pair generator.

Produces balanced, diverse compatible/incompatible profile pairs across the
preference hierarchy (dealbreakers > values > lifestyle > interests). Each topic
has two opposing positions; a compatible pair shares/complements positions, an
incompatible pair opposes them. Gender prefixes and templates are varied so the
dataset passes the diversity/bias quality dimensions.
"""

from __future__ import annotations

import random

# category -> {subcategory: (position_a, position_b)} where each position is
# (self_description, partner_preference).
TOPICS: dict[str, dict[str, tuple[tuple[str, str], tuple[str, str]]]] = {
    "dealbreakers": {
        "smoking": (
            ("never smokes and keeps a smoke-free home", "is a non-smoker"),
            ("smokes daily and enjoys it", "is comfortable around smoking"),
        ),
        "children": (
            ("definitely wants to have children someday", "wants kids in the future"),
            ("is child-free by choice and certain about it", "does not want children"),
        ),
        "drinking": (
            ("is completely sober and does not drink", "shares a sober lifestyle"),
            ("drinks often and loves a night out", "enjoys drinking together"),
        ),
        "monogamy": (
            ("is strictly monogamous and committed", "wants a monogamous relationship"),
            ("practices ethical non-monogamy", "is open to non-monogamy"),
        ),
    },
    "values": {
        "religion": (
            ("is deeply religious and attends services weekly", "shares a strong faith"),
            ("is secular and not religious at all", "is non-religious"),
        ),
        "family": (
            ("is very close with family and sees them often", "values close family ties"),
            ("is independent and keeps family at a distance", "prefers independence from family"),
        ),
        "ambition": (
            ("is career-driven and highly ambitious", "is goal-oriented and driven"),
            ("prioritizes a relaxed, slow-paced life", "values a laid-back lifestyle"),
        ),
        "honesty": (
            ("believes in radical honesty and openness", "is direct and transparent"),
            ("keeps things private and guarded", "respects a private nature"),
        ),
    },
    "lifestyle": {
        "fitness": (
            ("works out daily and loves staying active", "leads an active lifestyle"),
            ("prefers a sedentary routine and relaxing", "is happy taking it easy"),
        ),
        "diet": (
            ("is a committed vegan", "shares plant-based eating"),
            ("is a dedicated meat-lover", "enjoys eating meat together"),
        ),
        "finances": (
            ("is a frugal saver and budgets carefully", "is financially cautious"),
            ("is a free spender who loves treating themselves", "enjoys spending freely"),
        ),
        "social": (
            ("is an extrovert who loves big gatherings", "is outgoing and social"),
            ("is an introvert who prefers quiet nights in", "enjoys calm evenings at home"),
        ),
    },
    "interests": {
        "travel": (
            ("loves spontaneous travel and adventure", "enjoys exploring new places"),
            ("prefers staying home and routine", "is a homebody"),
        ),
        "music": (
            ("is passionate about live concerts and festivals", "shares a love of live music"),
            ("dislikes loud music and crowds", "prefers quiet settings"),
        ),
        "outdoors": (
            ("spends weekends hiking and camping", "loves the outdoors"),
            ("prefers indoor hobbies and comfort", "enjoys cozy indoor time"),
        ),
        "reading": (
            ("is an avid reader of literary fiction", "shares a love of books"),
            ("never reads and prefers video games", "is into gaming over reading"),
        ),
    },
}

_GENDERS = ["man", "woman", "man", "woman", "nonbinary person"]
# Descriptions are third-person clauses ("is a vegan", "loves travel"), so all
# templates wrap them with "who" to stay grammatical.
_SELF_TEMPLATES = [
    "I'm a {g} who {d}.",
    "Hi, I'm a {g} who {d}.",
    "As a {g}, I'm someone who {d}.",
    "I'm a {g} and someone who {d}.",
]
_PREF_TEMPLATES = [
    "I'm looking for a partner who {p}.",
    "I want to meet someone who {p}.",
    "My ideal match {p}.",
    "Ideally my partner {p}.",
]

_CAT_PREFIX = {
    "dealbreakers": "dealbreaker",
    "values": "values",
    "lifestyle": "lifestyle",
    "interests": "interests",
}


def _self_text(rng: random.Random, desc: str) -> str:
    g = rng.choice(_GENDERS)
    return rng.choice(_SELF_TEMPLATES).format(g=g, d=desc)


def _make_pair(rng: random.Random, category: str, subcat: str, compatible: bool) -> dict:
    pos_a, pos_b = TOPICS[category][subcat]
    seeker_pos = rng.choice([pos_a, pos_b])
    other_pos = seeker_pos if compatible else (pos_b if seeker_pos is pos_a else pos_a)

    text_1 = (
        f"{_self_text(rng, seeker_pos[0])} {rng.choice(_PREF_TEMPLATES).format(p=seeker_pos[1])}"
    )
    text_2 = _self_text(rng, other_pos[0])
    pair_type = f"{_CAT_PREFIX[category]}_{'aligned' if compatible else 'conflict'}"
    return {
        "text_1": text_1,
        "text_2": text_2,
        "label": 1 if compatible else 0,
        "category": category,
        "subcategory": subcat,
        "pair_type": pair_type,
    }


def _make_multi_pair(rng: random.Random) -> dict:
    cats = rng.sample(list(TOPICS), 2)
    parts_1, parts_2 = [], []
    aligns = []
    for cat in cats:
        subcat = rng.choice(list(TOPICS[cat]))
        compatible = rng.random() < 0.5
        aligns.append(compatible)
        pos_a, pos_b = TOPICS[cat][subcat]
        seeker = rng.choice([pos_a, pos_b])
        other = seeker if compatible else (pos_b if seeker is pos_a else pos_a)
        parts_1.append(seeker[0])
        parts_2.append(other[0])
    g1, g2 = rng.choice(_GENDERS), rng.choice(_GENDERS)
    text_1 = f"I'm a {g1} who {parts_1[0]} and {parts_1[1]}."
    text_2 = f"I'm a {g2} who {parts_2[0]} and {parts_2[1]}."
    label = 1 if all(aligns) else 0
    return {
        "text_1": text_1,
        "text_2": text_2,
        "label": label,
        "category": "multi",
        "subcategory": "+".join(cats),
        "pair_type": "multi_preference",
    }


def generate_pairs(n: int, seed: int = 0) -> list[dict]:
    """Generate ``n`` balanced dating pairs (~50/50 labels, even categories)."""
    rng = random.Random(seed)
    flat = [(cat, sub) for cat, subs in TOPICS.items() for sub in subs]
    pairs: list[dict] = []
    for i in range(n):
        compatible = i % 2 == 0  # exact label balance
        if i % 9 == 8:  # ~11% multi-preference pairs
            pair = _make_multi_pair(rng)
        else:
            cat, sub = flat[rng.randrange(len(flat))]
            pair = _make_pair(rng, cat, sub, compatible)
        pairs.append(pair)
    rng.shuffle(pairs)
    return pairs


def dataset_metadata(pairs: list[dict]) -> dict:
    from collections import Counter

    return {
        "count": len(pairs),
        "compatible": sum(p["label"] for p in pairs),
        "by_category": dict(Counter(p["category"] for p in pairs)),
        "by_pair_type": dict(Counter(p["pair_type"] for p in pairs)),
    }
