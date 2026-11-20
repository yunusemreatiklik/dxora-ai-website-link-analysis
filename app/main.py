"""Dxora assessment: stage 3 website extraction + real LLM analysis."""
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from app.schemas import LinkAnalysisRequest
from app.services.llm_service import LLMServiceError, MissingAPIKey, analyze_with_gemini
from app.services.website_extractor import (
    ContentTooLarge,
    UnsupportedContent,
    WebsiteFetchError,
    fetch_website,
)
from app.utils.validators import UnsafeURL

load_dotenv()  # Local .env only; never commit real credentials.

app = FastAPI(
    title="Dxora AI-Powered Website Link Analysis",
    description="Stage 3: extract real website content and analyze it through the Gemini API",
    version="0.3.0",
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.3.0"}


@app.post("/link-analysis")
async def link_analysis(request: LinkAnalysisRequest):
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

    return {
        "success": True,
        "status": "analysis_complete",
        "website": page.final_url,
        "brand": ai.result.brand.model_dump(),
        "analysis": ai.result.analysis.model_dump(),
        "model_info": {"provider": ai.provider, "model": ai.model, "token_usage": ai.usage},
        "source_summary": {
            "title": page.title,
            "meta_description": page.meta_description,
            "characters_extracted": page.characters_extracted,
        },
        "limitations": [
            "Competitor suggestions are not independently verified by this API",
            "SEO keyword recommendations are not actual measured search volumes",
            "Dynamic JavaScript-only content may not appear in extracted HTML",
        ],
    }
