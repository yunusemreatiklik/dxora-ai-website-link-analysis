"""Regression tests added for the v1.0 hardening release."""
import asyncio
import httpx
import pytest
from fastapi.testclient import TestClient
from app.limits import DemoLimiter
from app.main import app
from app.schemas import AIAnalysis
from app.services.website_extractor import _fetch_with_client
from app.utils.validators import UnsafeURL, require_public_website
from scripts.benchmark_gemini import estimate_cost


def test_swagger_has_typed_json_schema():
    schema = TestClient(app).get("/openapi.json").json()
    endpoint = schema["paths"]["/link-analysis"]["post"]
    assert "200" in endpoint["responses"]
    assert "LinkAnalysisResponse" in str(endpoint["responses"]["200"])


def test_limiter_per_client_and_releases_slots():
    limit = DemoLimiter(per_minute=1, per_day=2, parallel=1)
    assert limit.reserve("a") is None
    assert "concurrent" in limit.reserve("b")
    limit.release()
    assert "rate" in limit.reserve("a")
    assert limit.reserve("b") is None
    limit.release()
    assert "budget" in limit.reserve("c")


def test_limiter_rejects_without_unlocking():
    limit = DemoLimiter(per_minute=1, per_day=1, parallel=1)
    assert limit.reserve("1") is None
    assert limit.reserve("1") is not None
    limit.release()
    assert limit.reserve("2") is not None


def test_pinned_connection_retains_original_host_and_tls_name(monkeypatch):
    async def resolve(_):
        return "93.184.215.14"
    monkeypatch.setattr("app.services.website_extractor.require_public_website", resolve)
    def handler(request):
        assert request.url.host == "93.184.215.14"
        assert request.headers["Host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<h1>Example</h1>")
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            page = await _fetch_with_client("https://example.com/home", client, pin_dns=True)
            assert page.final_url == "https://example.com/home"
    asyncio.run(go())


def test_block_invalid_address_and_credentials():
    for address in ("http://127.0.0.1/admin", "http://169.254.169.254/latest/meta-data", "https://u:p@example.com"):
        with pytest.raises(UnsafeURL):
            asyncio.run(require_public_website(address))


def test_url_length_guard():
    with pytest.raises(UnsafeURL):
        asyncio.run(require_public_website("https://example.com/" + "a" * 3000))


def test_cost_formula():
    assert abs(estimate_cost("gemini-3.5-flash-lite", 1656, 1236) - 0.0035868) < 1e-9


def test_optional_fields_present_in_schema():
    assert "potential_interests" in AIAnalysis.model_json_schema().__str__()
    assert "customer_profiles" in AIAnalysis.model_json_schema().__str__()
