"""FastAPI endpoint tests using TestClient (no live LLM calls)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


def test_review_resume_returns_labels(client: TestClient, sample_resume, sample_job):
    payload = {
        "resume": sample_resume.model_dump(),
        "job": sample_job.model_dump(),
        "enable_judge": False,
    }
    response = client.post("/review-resume", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "labels" in data
    assert "skills_overlap" in data["labels"]
    assert isinstance(data["labels"]["experience_mismatch"], bool)
    assert data["judge"] is None


def test_review_resume_validation_status(client: TestClient, sample_resume, sample_job):
    payload = {
        "resume": sample_resume.model_dump(),
        "job": sample_job.model_dump(),
        "enable_judge": False,
    }
    response = client.post("/review-resume", json=payload)
    data = response.json()
    assert "validation_passed" in data
    assert isinstance(data["validation_passed"], bool)


def test_failure_rates_404_when_no_summary(client: TestClient, tmp_path, monkeypatch):
    from pipeline import config as cfg_module

    def fake_settings():
        s = cfg_module.Settings(
            openai_api_key="sk-test",
            data_dir=tmp_path,
            visuals_dir=tmp_path,
        )
        return s

    monkeypatch.setattr("api.routes.get_settings", fake_settings)
    response = client.get("/analysis/failure-rates")
    assert response.status_code == 404
