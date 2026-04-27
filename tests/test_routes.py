import uuid

import pytest
from litestar.testing import TestClient

from guess_explainr import state
from guess_explainr.app import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Test client with config isolated to a temp directory."""
    monkeypatch.setattr(state, "_config_file", str(tmp_path / "config.json"))
    with TestClient(app=app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/new-chat-id
# ---------------------------------------------------------------------------


def test_new_chat_id_returns_uuid(client):
    r = client.get("/api/new-chat-id")
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    uuid.UUID(body["id"])  # raises ValueError if not a valid UUID


def test_new_chat_id_unique(client):
    id1 = client.get("/api/new-chat-id").json()["id"]
    id2 = client.get("/api/new-chat-id").json()["id"]
    assert id1 != id2


# ---------------------------------------------------------------------------
# GET /api/panorama-image
# ---------------------------------------------------------------------------


def test_panorama_image_404_when_no_image(client):
    r = client.get("/api/panorama-image")
    assert r.status_code == 404


def test_panorama_image_returns_jpeg_bytes(client):
    state.panorama_state.panorama_image_bytes = b"\xff\xd8\xff\xe0fake-jpeg"
    r = client.get("/api/panorama-image")
    assert r.status_code == 200
    assert r.content == b"\xff\xd8\xff\xe0fake-jpeg"
    assert r.headers["content-type"].startswith("image/jpeg")


# ---------------------------------------------------------------------------
# POST /api/compare
# ---------------------------------------------------------------------------


def test_compare_no_countries_returns_400(client):
    r = client.post("/api/compare", json={"compare_countries": [], "questions": ""})
    assert r.status_code == 400


def test_compare_valid_renders_stream_url(client):
    r = client.post("/api/compare", json={"compare_countries": ["france"], "questions": ""})
    assert r.status_code in (200, 201)
    body = r.json()
    assert "analysis-stream" in body["stream_url"]
    assert "france" in body["stream_url"]


def test_compare_multiple_countries(client):
    r = client.post(
        "/api/compare",
        json={"compare_countries": ["france", "germany"], "questions": ""},
    )
    assert r.status_code in (200, 201)
    body = r.json()
    assert "france" in body["stream_url"]
    assert "germany" in body["stream_url"]


# ---------------------------------------------------------------------------
# GET /api/analysis-stream
# ---------------------------------------------------------------------------


def test_analysis_stream_missing_param_returns_400(client):
    r = client.get("/api/analysis-stream")
    assert r.status_code == 400


def test_analysis_stream_empty_countries_returns_400(client):
    r = client.get("/api/analysis-stream?countries=")
    assert r.status_code == 400


def test_analysis_stream_whitespace_only_returns_400(client):
    r = client.get("/api/analysis-stream?countries=++++")
    assert r.status_code == 400


def test_analysis_stream_streams_and_closes(client, monkeypatch):
    async def _fake_stream(country_ids, questions, *, only_delta):
        yield "**Greece** has white buildings."

    monkeypatch.setattr("guess_explainr.routes.step4.stream_analysis", _fake_stream)
    state.panorama_state.panorama_image_bytes = b"fake"

    r = client.get("/api/analysis-stream?countries=greece")
    assert r.status_code == 200
    # SSE body must end with a done event
    assert "event: done" in r.text


def test_analysis_stream_error_emits_done(client, monkeypatch):
    async def _failing_stream(country_ids, questions, *, only_delta):
        raise RuntimeError("LLM unavailable")
        yield  # make it an async generator

    monkeypatch.setattr("guess_explainr.routes.step4.stream_analysis", _failing_stream)
    state.panorama_state.panorama_image_bytes = b"fake"

    r = client.get("/api/analysis-stream?countries=france")
    assert r.status_code == 200
    # Error path must still close the stream with an error event
    assert "event: error" in r.text
    assert "LLM unavailable" in r.text


# ---------------------------------------------------------------------------
# GET /api/config
# ---------------------------------------------------------------------------


def test_config_not_configured_by_default(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    assert r.json() == {"configured": False}


# ---------------------------------------------------------------------------
# POST /api/config  →  GET /api/config
# ---------------------------------------------------------------------------


def test_save_config_then_reports_configured(client):
    r = client.post(
        "/api/config",
        json={
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "api_key": "sk-ant-test",
            "maps_api_key": "",
        },
    )
    assert r.status_code in (200, 201)
    r2 = client.get("/api/config")
    assert r2.json()["configured"] is True


def test_save_config_persists_to_disk(client, tmp_path, monkeypatch):
    monkeypatch.setattr(state, "_config_file", str(tmp_path / "config.json"))
    client.post(
        "/api/config",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "sk-openai",
            "maps_api_key": "",
        },
    )
    cfg = state.get_config()
    assert cfg.ai_model == "gpt-4o"
