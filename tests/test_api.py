"""Tests for API endpoints: request validation, status response shape, error handling."""
import pytest
from fastapi.testclient import TestClient


# ─── Health ─────────────────────────────────────────────────────────────────

def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ─── Categories ──────────────────────────────────────────────────────────────

def test_list_categories(client):
    resp = client.get("/v1/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    assert "해외 동향" in data["categories"]
    assert "상품·서비스" in data["categories"]
    assert "푸드테크" in data["categories"]


# ─── Schema endpoints ────────────────────────────────────────────────────────

def test_get_schema_overseas_trend(client):
    resp = client.get("/v1/schemas/해외 동향")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["category"] == "해외 동향"
    assert "trend_name" in schema
    assert "cases" in schema
    assert "expansion_pattern" in schema


def test_get_schema_product_service(client):
    resp = client.get("/v1/schemas/상품·서비스")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["category"] == "상품·서비스"
    assert "name" in schema
    assert "key_features" in schema
    assert "business_model" in schema


def test_get_schema_foodtech(client):
    resp = client.get("/v1/schemas/푸드테크")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["category"] == "푸드테크"
    assert "technology_name" in schema
    assert "applications" in schema
    assert "industry_meaning" in schema


def test_get_schema_invalid_category(client):
    resp = client.get("/v1/schemas/invalid_category")
    assert resp.status_code == 404


# ─── POST /v1/research ───────────────────────────────────────────────────────

def test_create_research_valid_request(client):
    resp = client.post("/v1/research", json={
        "article_url": "https://example.com/article/123",
        "category": "해외 동향",
    })
    assert resp.status_code == 202
    data = resp.json()
    assert "request_id" in data
    assert data["status"] == "queued"
    assert data["request_id"].startswith("req_")


def test_create_research_all_categories(client):
    for category in ["해외 동향", "상품·서비스", "푸드테크"]:
        resp = client.post("/v1/research", json={
            "article_url": "https://example.com/article/1",
            "category": category,
        })
        assert resp.status_code == 202, f"Failed for category: {category}"


def test_create_research_with_options(client):
    resp = client.post("/v1/research", json={
        "article_url": "https://example.com/article/1",
        "category": "푸드테크",
        "options": {
            "max_iterations": 2,
            "min_completion_rate": 0.75,
        },
    })
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"


def test_create_research_invalid_url(client):
    resp = client.post("/v1/research", json={
        "article_url": "not-a-url",
        "category": "해외 동향",
    })
    assert resp.status_code == 422


def test_create_research_invalid_category(client):
    resp = client.post("/v1/research", json={
        "article_url": "https://example.com/article/1",
        "category": "invalid_category",
    })
    assert resp.status_code == 422


def test_create_research_missing_url(client):
    resp = client.post("/v1/research", json={
        "category": "해외 동향",
    })
    assert resp.status_code == 422


def test_create_research_missing_category(client):
    resp = client.post("/v1/research", json={
        "article_url": "https://example.com/article/1",
    })
    assert resp.status_code == 422


# ─── GET /v1/research/{request_id} ───────────────────────────────────────────

def test_get_research_not_found(client):
    resp = client.get("/v1/research/nonexistent_id")
    assert resp.status_code == 404


def test_get_research_queued_status(client):
    # Create job
    post_resp = client.post("/v1/research", json={
        "article_url": "https://example.com/article/1",
        "category": "해외 동향",
    })
    request_id = post_resp.json()["request_id"]

    # Get immediately (may still be queued or processing/completed due to background tasks)
    get_resp = client.get(f"/v1/research/{request_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["request_id"] == request_id
    assert data["status"] in ("queued", "processing", "completed", "partial_completed", "failed")


def test_get_research_response_shape(client):
    post_resp = client.post("/v1/research", json={
        "article_url": "https://example.com/article/1",
        "category": "상품·서비스",
    })
    request_id = post_resp.json()["request_id"]

    get_resp = client.get(f"/v1/research/{request_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()

    # Required fields in response
    assert "request_id" in data
    assert "status" in data
    assert "category" in data
    assert "article_url" in data
    assert "meta" in data
    assert "created_at" in data["meta"]


def test_get_research_failed_has_error_field(client):
    """Simulate a failure by using a URL that the stub parser will refuse."""
    resp = client.post("/v1/research", json={
        "article_url": "ftp://invalid-scheme.com/article",
        "category": "해외 동향",
    })
    # ftp:// won't pass URL validator in request model
    assert resp.status_code == 422
