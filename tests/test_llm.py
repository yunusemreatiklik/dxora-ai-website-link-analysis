"""Offline contract tests; they do not call Gemini or spend API credits."""
import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_service import (
    LLMServiceError,
    MissingAPIKey,
    _parse_response,
    analyze_with_gemini,
    build_prompt,
)
from app.services.website_extractor import ExtractedWebsite


def page():
    return ExtractedWebsite(
        final_url="https://example.com/",
        title="Example Ltd",
        meta_description="Software company",
        headings=["Web development", "Cloud consulting"],
        text="Example Ltd offers web development and cloud consulting to startups.",
        characters_extracted=74,
    )


def analysis_payload():
    return {
        "brand": {"name": "Example Ltd", "category": "IT services", "summary": "Software developer"},
        "analysis": {
            "competitor_analysis": {
                "brand_overview": "IT consultancy",
                "competitors": [{"name": "Potential competitor", "main_service": "Consulting", "strengths": ["Example"], "weaknesses_or_gaps": ["Unverified"], "evidence_status": "unverified_suggestion", "evidence_url": None}],
                "strengths": ["Specialized"], "opportunities": ["Improve positioning"],
            },
            "target_search_queries": [
                {"query": f"IT services {i}", "platforms": [p], "intent": "Service search", "business_relevance": "Relevant", "target_audience": "Startups"}
                for i, p in enumerate(["Google", "Facebook", "Instagram", "LinkedIn", "X"])
            ],
            "seo_improvements": {
                "primary_keyword": "IT services", "secondary_keywords": ["web development"],
                "long_tail_keywords": ["web development for startups"],
                "recommended_title": "Web development for startups", "meta_description": "Services for startups", "supporting_content": ["FAQ page"],
            },
            "top_services": [
                {"name": f"Service {i}", "description": "Business service", "target_industry": "IT", "target_customer": "Startup", "main_benefit": "Presence", "evidence_status": "website_content" if i == 0 else "inferred_suggestion"}
                for i in range(5)
            ],
            "target_audience": {
                "primary_audience": ["Startups"], "secondary_audience": ["SMEs"],
                "industries": ["Tech"], "business_types": ["B2B"],
                "customer_needs": ["Web app"], "geographic_focus": [],
                "recommended_segments": ["Early-stage startups"],
            },
        },
    }


def gemini_mock_body():
    return {
        "candidates": [{"content": {"parts": [{"text": json.dumps(analysis_payload())}]}}],
        "usageMetadata": {"promptTokenCount": 111, "candidatesTokenCount": 200, "totalTokenCount": 311},
    }


def test_build_prompt_explicitly_marks_untrusted_data():
    prompt = build_prompt(page())
    assert "UNTRUSTED DATA" in prompt
    assert "Example Ltd" in prompt
    assert "FIVE" in prompt


def test_parse_success_and_five_queries():
    parsed = _parse_response(gemini_mock_body())
    assert len(parsed.analysis.target_search_queries) == 5
    assert parsed.brand.name == "Example Ltd"


def test_missing_competitor_verification_not_asserted():
    p = _parse_response(gemini_mock_body())
    assert p.analysis.competitor_analysis.competitors[0].evidence_status == "unverified_suggestion"


def test_reject_missing_analysis_section():
    body = gemini_mock_body()
    payload = analysis_payload()
    del payload["analysis"]["target_audience"]
    body["candidates"][0]["content"]["parts"][0]["text"] = json.dumps(payload)
    with pytest.raises(LLMServiceError):
        _parse_response(body)


def test_reject_four_queries():
    p = analysis_payload()
    p["analysis"]["target_search_queries"].pop()
    with pytest.raises(LLMServiceError):
        _parse_response({"candidates": [{"content": {"parts": [{"text": json.dumps(p)}]}}]})


def test_no_key_fails(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(MissingAPIKey):
        asyncio.run(analyze_with_gemini(page()))


def test_gemini_request_mock_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-for-test")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-latest")

    def handler(request):
        assert request.headers["x-goog-api-key"] == "fake-for-test"
        data = json.loads(request.content)
        assert data["generationConfig"]["responseMimeType"] == "application/json"
        return httpx.Response(200, json=gemini_mock_body())

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            out = await analyze_with_gemini(page(), client)
            assert out.usage["total_tokens"] == 311
            assert out.model == "gemini-flash-latest"

    asyncio.run(check())


def test_gemini_http_failure_sanitized(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-do-not-print")

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(429))) as client:
            with pytest.raises(LLMServiceError) as exc:
                await analyze_with_gemini(page(), client)
            assert "429" in str(exc.value)
            assert "secret-do-not-print" not in str(exc.value)

    asyncio.run(check())


def test_endpoint_returns_five_sections(monkeypatch):
    async def fake_fetch(url):
        return page()

    async def fake_analyze(_page):
        from app.services.llm_service import LLMResult
        return LLMResult(_parse_response(gemini_mock_body()), "gemini", "unit-test", {"input_tokens": 5})

    monkeypatch.setattr("app.main.fetch_website", fake_fetch)
    monkeypatch.setattr("app.main.analyze_with_gemini", fake_analyze)
    result = TestClient(app).post("/link-analysis", json={"url": "https://example.com"})
    assert result.status_code == 200
    result = result.json()
    assert result["success"] is True
    assert len(result["analysis"]) == 5
    assert result["status"] == "analysis_complete"


def test_endpoint_missing_key_is_not_fake_success(monkeypatch):
    async def fake_fetch(url):
        return page()

    async def no_key(_page):
        raise MissingAPIKey("GEMINI_API_KEY is not configured")

    monkeypatch.setattr("app.main.fetch_website", fake_fetch)
    monkeypatch.setattr("app.main.analyze_with_gemini", no_key)
    result = TestClient(app).post("/link-analysis", json={"url": "https://example.com"})
    assert result.status_code == 503
    assert "GEMINI_API_KEY" in result.json()["detail"]
