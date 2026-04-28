from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import RunResponse

client = TestClient(app)

CATALOG_SLUGS = [
    "stripe", "shopify", "notion", "airbnb", "github",
    "figma", "linear", "vercel", "openai", "anthropic",
    "slack", "canva", "duolingo", "spotify", "doordash",
    "uber", "coinbase", "robinhood", "netflix", "discord",
    "zoom", "dropbox", "atlassian", "hubspot", "calendly",
    "walmart",
]


def test_health() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_catalog_returns_all_tiles() -> None:
    r = client.get("/api/catalog")
    assert r.status_code == 200
    body = r.json()
    slugs = {tile["slug"] for tile in body["companies"]}
    assert slugs == set(CATALOG_SLUGS), f"missing or extra slugs: {slugs ^ set(CATALOG_SLUGS)}"
    for tile in body["companies"]:
        assert tile["mark"]["bg"].startswith("#")
        assert 0 <= tile["top_score_preview"] <= 100


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_run_returns_canonical_shape_for_catalog(slug: str) -> None:
    r = client.get(f"/api/run?domain={slug}.com")
    assert r.status_code == 200, r.text
    parsed = RunResponse.model_validate(r.json())
    assert parsed.company.slug == slug
    assert parsed.company.tier == "catalog"
    assert parsed.top_epic.rice.composite > 0
    assert len(parsed.ingest.stream_samples) >= 12
    assert len(parsed.clusters) >= 5
    assert any(c.is_top for c in parsed.clusters)
    assert len(parsed.top_epic.acceptance_criteria) == 4
    assert len(parsed.top_epic.evidence) == 3


@pytest.mark.parametrize(
    "raw",
    [
        "https://www.stripe.com/atlas",
        "STRIPE",
        "stripe",
        "stripe.com",
    ],
)
def test_run_normalizes_input(raw: str) -> None:
    r = client.get("/api/run", params={"domain": raw})
    assert r.status_code == 200, r.text
    assert r.json()["company"]["slug"] == "stripe"


def test_run_unknown_domain_falls_through_to_synth() -> None:
    r = client.get("/api/run?domain=this-is-not-a-catalog-company.io")
    assert r.status_code == 200
    body = r.json()
    assert body["company"]["tier"] == "synth"
    assert body["meta"]["generator"] == "synth"
    parsed = RunResponse.model_validate(body)
    assert 78.0 <= parsed.top_epic.rice.composite <= 95.5


def test_run_synth_is_deterministic_across_requests() -> None:
    r1 = client.get("/api/run?domain=this-is-a-novel-domain.io").json()
    r2 = client.get("/api/run?domain=this-is-a-novel-domain.io").json()
    assert r1 == r2


def test_run_invalid_input_returns_400() -> None:
    # Empty + whitespace are caught by FastAPI's min_length=1 validator first → 422.
    # Pass a value that survives that gate but fails normalize().
    r = client.get("/api/run", params={"domain": "/"})
    assert r.status_code in (400, 422)


def test_run_stream_returns_sse_content_type() -> None:
    # Don't drain the stream (would take 22s). Just confirm the connection opens
    # and the headers indicate an event-stream.
    with client.stream("GET", "/api/run/stream?domain=stripe.com") as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")


def test_cors_preflight_present_on_run() -> None:
    r = client.options(
        "/api/run",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code in (200, 204)
    assert "access-control-allow-origin" in {k.lower() for k in r.headers.keys()}
