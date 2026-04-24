"""API endpoint tests (no GPU required — model loading is mocked)."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_health(client: TestClient):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "cuda_available" in data
    assert "loaded_models" in data


def test_list_models(client: TestClient):
    resp = client.get("/api/v1/models")
    assert resp.status_code == 200
    models = resp.json()
    assert isinstance(models, list)
    assert len(models) >= 4
    for m in models:
        assert "model_id" in m
        assert "name" in m


def test_summarize_text_too_short(client: TestClient, short_text: str):
    resp = client.post(
        "/api/v1/summarize",
        json={"text": short_text, "model_id": "sshleifer/distilbart-cnn-12-6"},
    )
    assert resp.status_code == 422  # Pydantic min_length validation


def test_summarize_mocked(client: TestClient, long_article: str):
    mock_result = MagicMock()
    mock_result.summary = "A mocked summary."
    mock_result.model_id = "sshleifer/distilbart-cnn-12-6"
    mock_result.input_tokens = 120
    mock_result.output_tokens = 20
    mock_result.compression_ratio = 6.0
    mock_result.latency_ms = 150.0
    mock_result.__dict__ = {
        "summary": "A mocked summary.",
        "model_id": "sshleifer/distilbart-cnn-12-6",
        "input_tokens": 120,
        "output_tokens": 20,
        "compression_ratio": 6.0,
        "latency_ms": 150.0,
    }

    mock_engine = MagicMock()
    mock_engine.summarize.return_value = mock_result

    with patch("api.routes.SummarizationEngine.get_or_create", return_value=mock_engine):
        resp = client.post(
            "/api/v1/summarize",
            json={
                "text": long_article,
                "model_id": "sshleifer/distilbart-cnn-12-6",
                "max_length": 100,
                "num_beams": 2,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == "A mocked summary."
    assert data["compression_ratio"] == 6.0


def test_compare_mocked(client: TestClient, long_article: str):
    mock_result = MagicMock()
    mock_result.__dict__ = {
        "summary": "Test summary.",
        "model_id": "sshleifer/distilbart-cnn-12-6",
        "input_tokens": 100,
        "output_tokens": 15,
        "compression_ratio": 6.7,
        "latency_ms": 200.0,
    }
    mock_engine = MagicMock()
    mock_engine.summarize.return_value = mock_result

    with patch("api.routes.SummarizationEngine.get_or_create", return_value=mock_engine):
        resp = client.post(
            "/api/v1/compare",
            json={"text": long_article, "model_ids": ["sshleifer/distilbart-cnn-12-6"]},
        )

    assert resp.status_code == 200
    assert "results" in resp.json()
