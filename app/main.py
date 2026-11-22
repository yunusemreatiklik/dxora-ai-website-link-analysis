"""Dxora: public website extraction and grounded five-section LLM analysis."""
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

from app.limits import DemoLimiter
from app.schemas import LinkAnalysisRequest, LinkAnalysisResponse, ModelInfo, SourceSummary, TokenUsage
from app.services.llm_service import LLMServiceError, MissingAPIKey, analyze_with_gemini
from app.services.website_extractor import (
    ContentTooLarge, UnsupportedContent, WebsiteFetchError, fetch_website,
)
from app.utils.validators import UnsafeURL

load_dotenv()

app = FastAPI(
    title="Dxora AI-Powered Website Link Analysis",
    description="Website extraction, validated Gemini analysis, five business intelligence sections",
    version="1.0.0",
)


def _positive_int(name: str, default: int, maximum: int) -> int:
    try:
        return max(1, min(int(os.getenv(name, default)), maximum))
    except ValueError:
        return default


limiter = DemoLimiter(
    per_minute=_positive_int("DEMO_REQUESTS_PER_MINUTE", 5, 100),
    per_day=_positive_int("DEMO_REQUESTS_PER_DAY", 75, 10000),
    parallel=_positive_int("DEMO_MAX_CONCURRENT", 2, 16),
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/link-analysis", response_model=LinkAnalysisResponse, responses={
    400: {"description": "Unsafe or invalid destination URL"},
    413: {"description": "HTML exceeds download limit"},
    415: {"description": "Non-HTML content"},
    429: {"description": "Demo rate limit or request budget exceeded"},
    502: {"description": "Website or Gemini provider failure"},
    503: {"description": "Gemini API key not configured"},
})
async def link_analysis(request: LinkAnalysisRequest, http_request: Request):
    peer = http_request.client.host if http_request.client else "unknown"
    rejection = limiter.reserve(peer)
    if rejection:
        raise HTTPException(status_code=429, detail=rejection, headers={"Retry-After": "60"})
    try:
        try:
            page = await fetch_website(str(request.url))
        except UnsafeURL as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except UnsupportedContent as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        except ContentTooLarge as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except WebsiteFetchError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        try:
            ai = await analyze_with_gemini(page)
        except MissingAPIKey as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LLMServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return LinkAnalysisResponse(
            success=True,
            status="analysis_complete",
            website=page.final_url,
            brand=ai.result.brand,
            analysis=ai.result.analysis,
            model_info=ModelInfo(
                provider=ai.provider,
                model=ai.model,
                token_usage=TokenUsage.model_validate(ai.usage),
                response_seconds=ai.response_seconds,
            ),
            source_summary=SourceSummary(
                title=page.title,
                meta_description=page.meta_description,
                characters_extracted=page.characters_extracted,
            ),
            limitations=[
                "Competitors not independently verified unless an evidence URL is provided",
                "Recommended search queries are not measured search volume data",
                "JavaScript-only content may be missing from the source HTML",
                "Inferred services are suggestions, not confirmed offerings",
            ],
        )
    finally:
        limiter.release()
