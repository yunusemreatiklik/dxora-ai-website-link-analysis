"""Offline regression tests for upstream Gemini errors and safe HTTP status mapping.

No Google API calls or real API credentials are used.
"""
import asyncio

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_service import (
    GeminiRateLimitError, GeminiUnavailableError, GeminiTimeoutError,
    analyze_with_gemini, _rate_limit_metadata,
)
from tests.test_llm import page, gemini_mock_body


def _daily_response():
    return httpx.Response(429, json={
        "error": {
            "code": 429,
            "message": "secret-api-key-should-not-be-displayed",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
                    {"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier", "quotaMetric": "requests"}
                ]},
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "3600s"},
            ],
        }
    })


def test_daily_quota_exhaustion_does_not_retry(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return _daily_response()

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            try:
                await analyze_with_gemini(page(), client)
            except GeminiRateLimitError as exc:
                assert exc.daily_quota is True
                assert exc.retry_after == 3600
                assert "429" in str(exc)
                assert "secret-api-key" not in str(exc)
            else:
                raise AssertionError("expected rate limit exception")

    asyncio.run(run())
    assert calls == 1


def test_missing_retry_metadata_does_not_hammer_provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"error": {"status": "RESOURCE_EXHAUSTED"}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            try:
                await analyze_with_gemini(page(), client)
            except GeminiRateLimitError as exc:
                assert exc.retry_after is None
            else:
                raise AssertionError("expected GeminiRateLimitError")

    asyncio.run(run())
    assert calls == 1


def test_short_explicit_retry_delay_allows_one_retry(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    calls = 0
    delays = []

    async def fake_sleep(seconds):
        delays.append(seconds)

    monkeypatch.setattr("app.services.llm_service.asyncio.sleep", fake_sleep)

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"retry-after": "2"})
        return httpx.Response(200, json=gemini_mock_body())

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await analyze_with_gemini(page(), client)
            assert result.result.brand.name == "Example Ltd"

    asyncio.run(run())
    assert calls == 2
    assert delays == [2]


def test_long_retry_after_returns_without_waiting(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"retry-after": "420"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            try:
                await analyze_with_gemini(page(), client)
            except GeminiRateLimitError as exc:
                assert exc.retry_after == 420
            else:
                raise AssertionError("expected rate limit")

    asyncio.run(run())
    assert calls == 1


def test_temporary_503_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    calls = 0
    delays = []

    async def fake_sleep(seconds):
        delays.append(seconds)

    monkeypatch.setattr("app.services.llm_service.asyncio.sleep", fake_sleep)

    def handler(request):
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=gemini_mock_body())

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await analyze_with_gemini(page(), client)
            assert result.model is not None

    asyncio.run(run())
    assert calls == 3
    assert delays == [1, 2]


def test_persistent_503_returns_typed_failure(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    calls = 0

    async def fake_sleep(seconds):
        pass

    monkeypatch.setattr("app.services.llm_service.asyncio.sleep", fake_sleep)

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            try:
                await analyze_with_gemini(page(), client)
            except GeminiUnavailableError as exc:
                assert "503" in str(exc)
            else:
                raise AssertionError("expected error")

    asyncio.run(run())
    assert calls == 3


def test_timeout_is_distinguished(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    calls = 0

    async def fake_sleep(seconds):
        pass

    monkeypatch.setattr("app.services.llm_service.asyncio.sleep", fake_sleep)

    def handler(request):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("slow upstream", request=request)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            try:
                await analyze_with_gemini(page(), client)
            except GeminiTimeoutError:
                pass
            else:
                raise AssertionError("expected timeout")

    asyncio.run(run())
    assert calls == 3


def test_structured_invalid_retry_info_is_ignored():
    response = httpx.Response(429, json={"error": {
        "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "not valid"}]
    }})
    assert _rate_limit_metadata(response) == (None, False)


def test_endpoint_propagates_provider_429_with_retry_header(monkeypatch):
    async def fake_fetch(url):
        return page()

    async def fake_analyze(_page):
        raise GeminiRateLimitError(retry_after=75, daily_quota=True)

    monkeypatch.setattr("app.main.fetch_website", fake_fetch)
    monkeypatch.setattr("app.main.analyze_with_gemini", fake_analyze)
    response = TestClient(app).post("/link-analysis", json={"url": "https://example.com"})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "75"
    assert "daily model quota" in response.json()["detail"]


def test_endpoint_maps_provider_503_separately_from_fetch_502(monkeypatch):
    async def fake_fetch(url):
        return page()

    async def fake_analyze(_page):
        raise GeminiUnavailableError("Gemini service temporarily unavailable")

    monkeypatch.setattr("app.main.fetch_website", fake_fetch)
    monkeypatch.setattr("app.main.analyze_with_gemini", fake_analyze)
    response = TestClient(app).post("/link-analysis", json={"url": "https://example.com"})
    assert response.status_code == 503


def test_endpoint_timeout_returns_504(monkeypatch):
    async def fake_fetch(url):
        return page()

    async def fake_analyze(_page):
        raise GeminiTimeoutError("Gemini API request timed out after retries")

    monkeypatch.setattr("app.main.fetch_website", fake_fetch)
    monkeypatch.setattr("app.main.analyze_with_gemini", fake_analyze)
    response = TestClient(app).post("/link-analysis", json={"url": "https://example.com"})
    assert response.status_code == 504
