"""Shared fixtures: sample feedback, sentiment, themes, roadmap."""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest  # noqa: E402

from pipeline.models import Feedback, RoadmapItem, SentimentResult, Theme  # noqa: E402


@pytest.fixture
def sample_feedback() -> list[Feedback]:
    return [
        Feedback(
            id="a1",
            source="amazon",
            text="The app keeps crashing on launch and is painfully slow.",
            rating=1,
        ),
        Feedback(
            id="y1",
            source="yelp",
            text="Checkout on mobile is confusing and takes too many steps.",
            rating=2,
        ),
        Feedback(
            id="s1",
            source="app_store",
            text="Love the new features, works great and fast!",
            rating=5,
        ),
    ]


@pytest.fixture
def sample_sentiment() -> list[SentimentResult]:
    return [
        SentimentResult(feedback_id="a1", sentiment="negative", confidence=0.9, pain_intensity=0.9),
        SentimentResult(feedback_id="y1", sentiment="negative", confidence=0.8, pain_intensity=0.6),
        SentimentResult(
            feedback_id="s1", sentiment="positive", confidence=0.95, pain_intensity=0.1
        ),
    ]


@pytest.fixture
def sample_themes() -> list[Theme]:
    return [
        Theme(
            theme_id="T1",
            name="App crashes and slowness",
            description="Users report frequent crashes and slow performance.",
            feedback_ids=["a1"],
            avg_pain=0.9,
            product_area="performance",
        ),
        Theme(
            theme_id="T2",
            name="Confusing mobile checkout",
            description="Checkout flow is hard to use on mobile.",
            feedback_ids=["y1"],
            avg_pain=0.6,
            product_area="usability",
        ),
        Theme(
            theme_id="T3",
            name="Pricing complaints",
            description="Users find pricing tiers confusing and expensive.",
            feedback_ids=[],
            avg_pain=0.7,
            product_area="pricing",
        ),
    ]


@pytest.fixture
def roadmap_items() -> list[RoadmapItem]:
    return [
        RoadmapItem(
            item_id="R1",
            title="Improve app load time and reduce crashes",
            description="Optimize startup and fix crashes.",
            product_area="performance",
            status="in_progress",
        ),
        RoadmapItem(
            item_id="R2",
            title="Redesign checkout flow for mobile users",
            description="Simplify mobile checkout.",
            product_area="usability",
            status="planned",
        ),
    ]
