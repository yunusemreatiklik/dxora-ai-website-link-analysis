"""No network or billable API calls. Regression suite for Gemini -> backup."""
import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import AIAnalysis
from app.services.fallback_service import (
    FallbackConfigurationError, FallbackRateLimitError, FallbackUnavailableError,
    analyze_with_fallback, analyze_with_openai_compatible,
)
from app.services.llm_service import GeminiUnavailableError, LLMResult, analyze_with_gemini
from tests.test_llm import page, analysis_payload


def backup_body():
    return {
        "choices": [{"message": {"content": json.dumps(analysis_payload())}}],
        "usage": {"prompt_tokens": 42, "completion_tokens": 88, "total_tokens": 130},
    }


def set_free(monkeypatch):
    monkeypatch.setenv("FALLBACK_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-fake-key")


def test_openrouter_json_response_and_usage(monkeypatch):
    set_free(monkeypatch)
    def handler(request):
        assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer secret-fake-key"
        payload = json.loads(request.content)
        assert payload["model"] == "openai/gpt-oss-20b:free"
        assert payload["response_format"] == {"type": "json_object"}
        assert payload["reasoning"] == {"enabled": False}
        assert "UNTRUSTED DATA" in payload["messages"][1]["content"]
        return httpx.Response(200, json=backup_body())
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await analyze_with_openai_compatible(page(), client=client)
            assert result.provider == "openrouter"
            assert result.result.brand.name == "Example Ltd"
            assert result.usage["total_tokens"] == 130
    asyncio.run(run())


def test_503_primary_triggers_backup_once(monkeypatch):
    set_free(monkeypatch)
    calls = {"primary": 0, "backup": 0}
    async def primary(_):
        calls["primary"] += 1
        raise GeminiUnavailableError("Gemini service temporarily unavailable")
    async def backup(_):
        calls["backup"] += 1
        return LLMResult(result=AIAnalysis.model_validate(analysis_payload()), provider="openrouter", model="openai/gpt-oss-20b:free", usage={})
    result = asyncio.run(analyze_with_fallback(page(), primary=primary, backup=backup))
    assert result.provider == "openrouter"
    assert calls == {"primary": 1, "backup": 1}


def test_successful_gemini_never_spends_free_backup_quota(monkeypatch):
    set_free(monkeypatch)
    async def primary(_):
        return LLMResult(result=AIAnalysis.model_validate(analysis_payload()), provider="gemini", model="test", usage={})
    async def backup(_):
        raise AssertionError("fallback should not be called")
    assert asyncio.run(analyze_with_fallback(page(), primary=primary, backup=backup)).provider == "gemini"


def test_fallback_disabled_keeps_existing_503_behavior(monkeypatch):
    monkeypatch.setenv("FALLBACK_PROVIDER", "none")
    async def primary(_):
        raise GeminiUnavailableError("Gemini temporarily unavailable")
    with pytest.raises(GeminiUnavailableError):
        asyncio.run(analyze_with_fallback(page(), primary=primary))


def test_paid_fallback_forbidden_by_default(monkeypatch):
    monkeypatch.setenv("FALLBACK_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    monkeypatch.delenv("ALLOW_PAID_FALLBACK", raising=False)
    with pytest.raises(FallbackConfigurationError, match="Paid fallback is disabled"):
        asyncio.run(analyze_with_openai_compatible(page()))


def test_openai_paid_fallback_requires_explicit_consent(monkeypatch):
    monkeypatch.setenv("FALLBACK_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.delenv("ALLOW_PAID_FALLBACK", raising=False)
    with pytest.raises(FallbackConfigurationError, match="Paid fallback is disabled"):
        asyncio.run(analyze_with_openai_compatible(page()))


def test_missing_key_does_not_expose_api_secrets(monkeypatch):
    set_free(monkeypatch)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(FallbackConfigurationError, match="key is not configured"):
        asyncio.run(analyze_with_openai_compatible(page()))


def test_fallback_quota_429_maps_retry_after(monkeypatch):
    set_free(monkeypatch)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(429, headers={"retry-after": "50"}, json={"error": "secret-fake-key"}))) as client:
            with pytest.raises(FallbackRateLimitError) as exc:
                await analyze_with_openai_compatible(page(), client=client)
            assert exc.value.retry_after == 50
            assert "secret-fake-key" not in str(exc.value)
    asyncio.run(run())


def test_backup_503_has_sanitized_message(monkeypatch):
    set_free(monkeypatch)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(503, text="SECRET INTERNAL PROVIDER ERROR"))) as client:
            with pytest.raises(FallbackUnavailableError) as exc:
                await analyze_with_openai_compatible(page(), client=client)
            assert "SECRET INTERNAL" not in str(exc.value)
    asyncio.run(run())


def test_malformed_fallback_fails_closed(monkeypatch):
    set_free(monkeypatch)
    bad = {"choices": [{"message": {"content": '{"brand":{}}'}}]}
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=bad))) as client:
            with pytest.raises(Exception, match="valid five-section JSON"):
                await analyze_with_openai_compatible(page(), client=client)
    asyncio.run(run())


def test_endpoint_503_transparently_uses_openrouter(monkeypatch):
    set_free(monkeypatch)
    async def fake_fetch(_):
        return page()
    async def fake_gemini(_):
        raise GeminiUnavailableError("Gemini returned HTTP 503")
    async def fake_fallback(_):
        from app.schemas import AIAnalysis
        return LLMResult(result=AIAnalysis.model_validate(analysis_payload()), provider="openrouter", model="openai/gpt-oss-20b:free", usage={})
    monkeypatch.setattr("app.main.fetch_website", fake_fetch)
    monkeypatch.setattr("app.main.analyze_with_gemini", fake_gemini)
    monkeypatch.setattr("app.services.fallback_service.analyze_with_openai_compatible", fake_fallback)
    response = TestClient(app).post("/link-analysis", json={"url": "https://example.com"})
    assert response.status_code == 200
    body = response.json()
    assert body["model_info"]["provider"] == "openrouter"
    assert any("alternate AI provider" in x for x in body["limitations"])


def test_endpoint_backup_rate_limit_returns_429(monkeypatch):
    async def fake_fetch(_): return page()
    async def fake_orchestrator(_page, primary):
        raise FallbackRateLimitError(32)
    monkeypatch.setattr("app.main.fetch_website", fake_fetch)
    monkeypatch.setattr("app.main.analyze_with_fallback", fake_orchestrator)
    r = TestClient(app).post("/link-analysis", json={"url": "https://example.com"})
    assert r.status_code == 429
    assert r.headers["retry-after"] == "32"


def test_primary_attempt_budget_can_be_reduced(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("GEMINI_MAX_ATTEMPTS", "1")
    calls = []
    def handler(req):
        calls.append(req.url)
        return httpx.Response(503, text="overloaded")
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(GeminiUnavailableError):
                await analyze_with_gemini(page(), client=client)
    asyncio.run(run())
    assert len(calls) == 1


def test_social_login_wall_403_does_not_invoke_llm(monkeypatch):
    from app.services.website_extractor import WebsiteAccessRestricted
    async def fake_fetch(_):
        raise WebsiteAccessRestricted("Source website restricts anonymous automated access")
    async def no_gemini(_):
        raise AssertionError("LLM must not be called when extraction fails")
    monkeypatch.setattr("app.main.fetch_website", fake_fetch)
    monkeypatch.setattr("app.main.analyze_with_gemini", no_gemini)
    r = TestClient(app).post("/link-analysis", json={"url": "https://www.instagram.com/p/example/"})
    assert r.status_code == 422
    assert "restricts" in r.json()["detail"]


def test_http_403_from_upstream_source_is_distinguished(monkeypatch):
    from app.services.website_extractor import fetch_website, WebsiteAccessRestricted
    async def allow_public(url): return "93.184.215.14"
    monkeypatch.setattr("app.services.website_extractor.require_public_website", allow_public)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda req: httpx.Response(403, text="private-data-must-not-leak")
        )) as client:
            with pytest.raises(WebsiteAccessRestricted) as exc:
                await fetch_website("https://www.instagram.com/p/example/", client=client)
            assert "private-data-must-not-leak" not in str(exc.value)
    asyncio.run(run())


def test_primary_one_attempt_429_preserves_error_type(monkeypatch):
    from app.services.llm_service import GeminiRateLimitError
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("GEMINI_MAX_ATTEMPTS", "1")
    seen = []
    def handler(req):
        seen.append(str(req.url))
        return httpx.Response(429, headers={"retry-after": "2"})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(GeminiRateLimitError) as exc:
                await analyze_with_gemini(page(), client=client)
            assert exc.value.retry_after == 2
    asyncio.run(run())
    assert len(seen) == 1


def test_reasoning_only_200_is_explained_not_reported_as_valid_json(monkeypatch):
    set_free(monkeypatch)
    body = {
        "model": "nvidia/nemotron-3.5-lightning:free",
        "choices": [{"finish_reason": "length", "message": {
            "content": None, "reasoning": "should never be echoed to the caller"
        }}],
        "usage": {"prompt_tokens": 2100, "completion_tokens": 6500},
    }
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json=body)
        )) as client:
            with pytest.raises(Exception, match="exhausted its output tokens on reasoning") as exc:
                await analyze_with_openai_compatible(page(), client=client)
            assert "should never be echoed" not in str(exc.value)
    asyncio.run(run())


def test_real_openrouter_model_name_is_reported(monkeypatch):
    set_free(monkeypatch)
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/free")
    body = backup_body()
    body["model"] = "google/gemma-4-31b-it:free"
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json=body)
        )) as client:
            result = await analyze_with_openai_compatible(page(), client=client)
            assert result.model == "google/gemma-4-31b-it:free"
    asyncio.run(run())


def test_openai_request_does_not_get_openrouter_reasoning_setting(monkeypatch):
    monkeypatch.setenv("FALLBACK_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("ALLOW_PAID_FALLBACK", "1")
    def handler(req):
        payload = json.loads(req.content)
        assert "reasoning" not in payload
        return httpx.Response(200, json=backup_body())
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await analyze_with_openai_compatible(page(), client=client)
    asyncio.run(run())


def test_metadata_only_returns_analysis_limited(monkeypatch):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    import app.main as main

    source = replace(
        page(),
        text="",
        headings=[],
        characters_extracted=0,
        title="CREST Instagram",
        meta_description="Claim Top Spot"
    )

    async def fake_extract(*args, **kwargs):
        return source

    async def fake_gemini(*args, **kwargs):
        return LLMResult(
            result=AIAnalysis.model_validate(analysis_payload()),
            provider="gemini",
            model="test-model",
            usage={}
        )

    monkeypatch.setattr(main, "fetch_website", fake_extract)
    monkeypatch.setattr(main, "analyze_with_gemini", fake_gemini)
    monkeypatch.setenv("FALLBACK_PROVIDER", "none")

    with TestClient(main.app) as client:
        response = client.post(
            "/link-analysis",
            json={"url": "https://instagram.com/crestspot"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "analysis_limited"
    assert data["source_summary"]["characters_extracted"] == 0
    assert any("Only source metadata" in x for x in data["limitations"])
