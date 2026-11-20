"""Retrieve and clean website HTML; no LLM claims are made at this stage."""

from dataclasses import dataclass
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx

from app.utils.validators import require_public_website

MAX_HTML_BYTES = 5_000_000
MAX_TEXT_CHARS = 15_000
MAX_REDIRECTS = 3


class WebsiteFetchError(Exception):
    """The upstream website could not be retrieved safely."""


class UnsupportedContent(WebsiteFetchError):
    """The remote resource is not an HTML page."""


class ContentTooLarge(WebsiteFetchError):
    """The remote HTML resource exceeds the size budget."""


@dataclass(frozen=True)
class ExtractedWebsite:
    final_url: str
    title: str
    meta_description: str
    headings: list[str]
    text: str
    characters_extracted: int


def parse_html(html: str, final_url: str) -> ExtractedWebsite:
    """Extract content with scripts, navigation, and boilerplate excluded."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if meta is None:
        meta = soup.find("meta", attrs={"property": "og:description"})
    description = str(meta.get("content") or "").strip() if meta else ""
    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"], limit=20)]
    headings = [h for h in headings if h][:15]

    for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        element.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    raw_text = root.get_text(" ", strip=True)
    cleaned = re.sub(r"\s+", " ", raw_text).strip()[:MAX_TEXT_CHARS]
    return ExtractedWebsite(
        final_url=final_url,
        title=title,
        meta_description=description,
        headings=headings,
        text=cleaned,
        characters_extracted=len(cleaned),
    )


async def fetch_website(url: str, client: httpx.AsyncClient | None = None) -> ExtractedWebsite:
    """Fetch a public HTML page, revalidating each redirect before following it."""
    if client is None:
        async with httpx.AsyncClient(
            follow_redirects=False,
            trust_env=False,
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={"User-Agent": "DxoraLinkAnalysisAssessment/0.2 (+Python HTTPX)"},
        ) as owned_client:
            return await _fetch_with_client(url, owned_client)
    return await _fetch_with_client(url, client)


async def _fetch_with_client(url: str, client: httpx.AsyncClient) -> ExtractedWebsite:
    current_url = url
    for redirect_count in range(MAX_REDIRECTS + 1):
        await require_public_website(current_url)
        try:
            async with client.stream("GET", current_url, follow_redirects=False) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise WebsiteFetchError("Redirect response has no Location header")
                    if redirect_count >= MAX_REDIRECTS:
                        raise WebsiteFetchError("Too many redirects")
                    current_url = urljoin(str(response.url), location)
                    continue

                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if not any(t in content_type for t in ("text/html", "application/xhtml+xml")):
                    raise UnsupportedContent("The supplied URL does not return HTML")

                total = 0
                chunks: list[bytes] = []
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_HTML_BYTES:
                        raise ContentTooLarge(f"Website HTML is larger than the permitted {MAX_HTML_BYTES // 1_000_000} MB")
                    chunks.append(chunk)
                html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
                return parse_html(html, str(response.url))
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError, httpx.ProtocolError) as exc:
            raise WebsiteFetchError("Website could not be retrieved successfully") from exc
    raise WebsiteFetchError("Redirect limit exceeded")
