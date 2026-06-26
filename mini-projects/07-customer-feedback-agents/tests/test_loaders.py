"""Tests that each loader normalizes raw records correctly."""

from __future__ import annotations

from pipeline.loaders import AmazonLoader, AppStoreLoader, YelpLoader


def test_amazon_normalize_concats_title_and_text():
    fb = AmazonLoader().normalize(
        {
            "title": "Great product",
            "text": "Works well",
            "rating": 5.0,
            "asin": "B001",
            "verified_purchase": True,
        }
    )
    assert fb is not None
    assert fb.source == "amazon"
    assert fb.text == "Great product\nWorks well"
    assert fb.rating == 5
    assert fb.metadata["asin"] == "B001"


def test_amazon_normalize_empty_returns_none():
    assert AmazonLoader().normalize({"title": "", "text": ""}) is None


def test_yelp_label_to_star():
    fb = YelpLoader().normalize({"label": 0, "text": "terrible experience"})
    assert fb.rating == 1  # label 0 -> 1 star
    assert YelpLoader().normalize({"label": 4, "text": "amazing"}).rating == 5


def test_appstore_uses_review_field():
    fb = AppStoreLoader().normalize(
        {"review": "App is buggy", "star": 2, "date": "2020-01-01", "package_name": "com.x"}
    )
    assert fb.source == "app_store"
    assert fb.text == "App is buggy"
    assert fb.rating == 2
    assert fb.metadata["package_name"] == "com.x"


def test_loader_filters_short_reviews():
    class _Fake(YelpLoader):
        def load_raw(self, sample_size):
            return [
                {"label": 0, "text": "too short"},
                {"label": 4, "text": "this review is definitely long enough to keep"},
            ]

    kept = _Fake().load(sample_size=2, min_length=30)
    assert len(kept) == 1
