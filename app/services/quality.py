"""Conservative, non-network evidence gate for the already fetched website HTML.

A matching name on the submitted site proves ONLY a name mention, not the accuracy
of strengths, weakness comparisons, sales metrics or service-benefit claims.
External competitors not found in the page remain explicitly unverified; their
URLs and excerpts must not be invented or accepted from model-generated text.
"""
from __future__ import annotations

import re

from app.schemas import AIAnalysis
from app.services.website_extractor import ExtractedWebsite


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def _source_mention(page: ExtractedWebsite, name: str) -> str | None:
    """Return a literal short excerpt ONLY when the full name is on the page.

    Match full ordered tokens, not the old one-keyword heuristic. The evidence
    quotation is taken verbatim from our fetched page fields, never from an LLM.
    """
    tokens = re.findall(r"[\w]+", name, flags=re.UNICODE)
    if not tokens or len(name.strip()) < 3:
        return None
    # Word boundaries + whitespace / punctuation separators. For example,
    # 'Jira Project Management' matches actual 'Jira project management software'.
    pattern = re.compile(r"(?<!\w)" + r"[\s\-]+".join(map(re.escape, tokens)) + r"(?!\w)", re.IGNORECASE)
    sources = [page.title, page.meta_description, *page.headings, page.text]
    for source in sources:
        match = pattern.search(source)
        if match:
            start = max(0, match.start() - 90)
            end = min(len(source), match.end() + 90)
            return source[start:end].strip()
    return None


def improve_and_audit(page: ExtractedWebsite, result: AIAnalysis) -> tuple[AIAnalysis, list[str]]:
    """Audit model-claimed evidence and attach only real source-mention excerpts.

    Keeps five-service and five-query API contracts. Doesn't pretend external
    research happened, doesn't fetch extra URLs, and never manufactures evidence.
    """
    notices: list[str] = []
    analysis = result.analysis

    sanitized_services = []
    downgraded = 0
    for service in analysis.top_services:
        excerpt = _source_mention(page, service.name)
        if service.evidence_status == "website_content" and excerpt:
            sanitized_services.append(service.model_copy(update={
                "evidence_status": "website_content",
                "evidence_url": page.final_url,
                "evidence_excerpt": excerpt,
            }))
        else:
            if service.evidence_status == "website_content":
                downgraded += 1
            sanitized_services.append(service.model_copy(update={
                "evidence_status": "inferred_suggestion",
                "evidence_url": None,
                "evidence_excerpt": None,
            }))
    if downgraded:
        notices.append(
            f"{downgraded} model-labelled website services lack an exact source name mention; "
            "downgraded to inferred_suggestion"
        )

    # Reject fabricated source references. A site mentioning a competitor's name
    # DOES NOT verify the claimed competitor's capabilities or disadvantages.
    competitors = []
    downgraded_competitors = 0
    for competitor in analysis.competitor_analysis.competitors:
        excerpt = _source_mention(page, competitor.name)
        if competitor.evidence_status == "mentioned_on_website" and excerpt:
            competitors.append(competitor.model_copy(update={
                "evidence_url": page.final_url,
                "evidence_excerpt": excerpt,
            }))
        else:
            if competitor.evidence_status == "mentioned_on_website":
                downgraded_competitors += 1
            competitors.append(competitor.model_copy(update={
                "evidence_status": "unverified_suggestion",
                "evidence_url": None,
                "evidence_excerpt": None,
            }))
    if downgraded_competitors:
        notices.append(
            f"{downgraded_competitors} claimed competitor source mentions were unsupported and "
            "downgraded to unverified_suggestion"
        )
    if not competitors:
        notices.append("No competitor candidates returned; external research would be required")
    elif len(competitors) < 3:
        notices.append("Fewer than three competitor candidates identified; do not invent missing names")

    revised_competitors = analysis.competitor_analysis.model_copy(update={"competitors": competitors})
    revised_analysis = analysis.model_copy(update={
        "competitor_analysis": revised_competitors,
        "top_services": sanitized_services,
    })

    # The brand product list must not include model inventions absent from the
    # submitted page. Source-verified service names can populate an empty list.
    actual_products = []
    for product in result.brand.main_products_services:
        if _source_mention(page, product) and product not in actual_products:
            actual_products.append(product)
    if len(actual_products) != len(result.brand.main_products_services):
        notices.append("Unsubstantiated brand product names were removed from the source-derived list")
    if not actual_products:
        actual_products = [s.name for s in sanitized_services if s.evidence_status == "website_content"]
        if actual_products:
            notices.append("Main brand products recovered from source-mentioned service names")
        else:
            notices.append("Main products/services could not be reliably recovered from source text")

    seo = analysis.seo_improvements
    if _normalize(seo.recommended_title) == _normalize(page.title):
        notices.append("Suggested SEO title repeats the current page title; improvement not demonstrated")
    if page.meta_description and _normalize(seo.meta_description) == _normalize(page.meta_description):
        notices.append("Suggested meta description repeats the current description")

    # A source mention of a service/competitor name does NOT validate its
    # feature comparison, business metric, benefits, or pricing statements.
    notices.append(
        "Evidence excerpts verify name mentions only; detailed claims about features, "
        "strengths, weaknesses and metrics require independent review"
    )
    revised_brand = result.brand.model_copy(update={"main_products_services": actual_products})
    return result.model_copy(update={
        "brand": revised_brand, "analysis": revised_analysis,
    }), notices
