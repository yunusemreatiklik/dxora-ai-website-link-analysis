import asyncio
import socket

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.website_extractor import (
    ContentTooLarge,
    UnsupportedContent,
    WebsiteFetchError,
    fetch_website,
    parse_html,
)
from app.utils.validators import UnsafeURL, require_public_website


def run(coroutine):
    return asyncio.run(coroutine)


def test_health():
    assert TestClient(app).get("/health").json()["status"] == "ok"


def test_invalid_url_schema():
    response = TestClient(app).post("/link-analysis", json={"url": "not-a-url"})
    assert response.status_code == 422


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/admin", "http://10.0.0.10", "http://169.254.169.254",
    "http://localhost", "https://foo.internal", "http://example.com:8080",
    "http://admin:secret@example.com", "ftp://example.com",
])
def test_reject_unsafe_url(url):
    with pytest.raises(UnsafeURL):
        run(require_public_website(url))


def test_dns_resolving_to_private_address(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.0.5", 443))]
    )
    with pytest.raises(UnsafeURL):
        run(require_public_website("https://public-looking.example"))


def test_parse_html():
    html = '<html><head><title>Acme Shop</title><meta name="description" content="Buy shoes"></head><body><nav>Menus</nav><main><h1>Men shoes</h1><p>Quality sneakers</p><script>secret</script></main></body></html>'
    page = parse_html(html, "https://www.example.com")
    assert page.title == "Acme Shop"
    assert page.meta_description == "Buy shoes"
    assert "Men shoes" in page.headings
    assert "Quality sneakers" in page.text
    assert "Menus" not in page.text
    assert "secret" not in page.text


def test_fetch_html_mocked(monkeypatch):
    async def allow_public(_url):
        return None

    monkeypatch.setattr("app.services.website_extractor.require_public_website", allow_public)

    def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html><title>Example</title><main><h1>Hi</h1><p>Actual page content</p></main></html>")

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            page = await fetch_website("https://example.com", client)
            assert page.title == "Example"
            assert "Actual page content" in page.text

    run(check())


def test_redirect_to_localhost_blocked(monkeypatch):
    async def fake_check(url):
        if "localhost" in url:
            raise UnsafeURL("Not public")

    monkeypatch.setattr("app.services.website_extractor.require_public_website", fake_check)

    def handler(request):
        return httpx.Response(302, headers={"location": "http://localhost/admin"})

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(UnsafeURL):
                await fetch_website("https://example.com", client)

    run(check())


def test_reject_non_html(monkeypatch):
    async def allow_public(_url):
        return None

    monkeypatch.setattr("app.services.website_extractor.require_public_website", allow_public)

    def handler(request):
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"some bytes")

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(UnsupportedContent):
                await fetch_website("https://example.com", client)

    run(check())


def test_response_too_large(monkeypatch):
    async def allow_public(_url):
        return None

    monkeypatch.setattr("app.services.website_extractor.require_public_website", allow_public)

    def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"x" * 5_000_001)

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(ContentTooLarge):
                await fetch_website("https://example.com", client)

    run(check())
