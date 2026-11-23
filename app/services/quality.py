"""Conservative, non-network evidence gate for the already fetched website HTML.

A matching name on the submitted site proves ONLY a name mention, not the accuracy
of strengths, weakness comparisons, sales metrics or service-benefit claims.
External competitors not found in the page remain explicitly unverified; their
URLs and excerpts must not be invented or accepted from model-generated text.
"""
from __future__ import annotations

import re

from app.schemas import AIAnalysis
from app.services.competitor_guard import clean_name, same_entity, is_own_brand
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


# Unsupported numerical performance / adoption claims must not be presented as
# facts merely because a model wrote them. This is deliberately a narrow gate:
# it does not purport to fact-check all non-numerical marketing statements.
_NUMERICAL_CLAIM = re.compile(
    r"\b\d[\d,.]*\s*(?:\+|%|million\b|billion\b|apps\b|customers\b|"
    r"companies\b|integrations\b|hours\b|countries\b|users\b)|"
    r"\b(?:hundreds|thousands|millions|billions) of\b",
    re.I,
)


def _unsupported_numbers(claim: str, source: str) -> bool:
    matches = list(_NUMERICAL_CLAIM.finditer(claim))
    if not matches:
        return False
    # Matching a numeric expression is at most evidence that the publisher
    # made the same claim, NOT independent third-party validation.
    normalized_source = _normalize(source)
    return any(_normalize(m.group()) not in normalized_source for m in matches)


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
    rejected_competitors = 0
    deduplicated_competitors = 0
    downgraded_competitors = 0
    for competitor in analysis.competitor_analysis.competitors:
        cleaned_name = clean_name(competitor.name)
        if cleaned_name is None or is_own_brand(cleaned_name, result.brand.name):
            rejected_competitors += 1
            continue
        if any(same_entity(cleaned_name, prior.name) for prior in competitors):
            deduplicated_competitors += 1
            continue
        excerpt = _source_mention(page, cleaned_name)
        if competitor.evidence_status == "mentioned_on_website" and excerpt:
            cleaned = competitor.model_copy(update={
                "name": cleaned_name,
                "evidence_url": page.final_url,
                "evidence_excerpt": excerpt,
            })
        else:
            if competitor.evidence_status == "mentioned_on_website":
                downgraded_competitors += 1
            cleaned = competitor.model_copy(update={
                "name": cleaned_name,
                "evidence_status": "unverified_suggestion",
                "evidence_url": None,
                "evidence_excerpt": None,
            })
        competitors.append(cleaned)
    if rejected_competitors:
        notices.append(f"Removed {rejected_competitors} placeholder, ambiguous or self-competitor names")
    if deduplicated_competitors:
        notices.append(f"Removed {deduplicated_competitors} duplicate competitor candidates")
    if downgraded_competitors:
        notices.append(
            f"{downgraded_competitors} claimed competitor source mentions were unsupported and "
            "downgraded to unverified_suggestion"
        )
    if not competitors:
        notices.append("No competitor candidates returned; external research would be required")
    elif len(competitors) < 3:
        notices.append("Fewer than three competitor candidates identified; do not invent missing names")

    # Avoid unverifiable numerical claims in model-authored competitive strengths.
    # Unverified qualitative comparisons remain suggestions, not facts.
    page_source = " ".join([page.title, page.meta_description, *page.headings, page.text])
    numerical_removed = 0

    def keep_source_metrics(claims: list[str]) -> list[str]:
        nonlocal numerical_removed
        kept = []
        for claim in claims:
            if _unsupported_numbers(claim, page_source):
                numerical_removed += 1
            else:
                kept.append(claim)
        return kept

    for index, competitor in enumerate(competitors):
        competitors[index] = competitor.model_copy(update={
            "strengths": keep_source_metrics(competitor.strengths),
            "weaknesses_or_gaps": keep_source_metrics(competitor.weaknesses_or_gaps),
        })
    revised_competitors = analysis.competitor_analysis.model_copy(update={
        "competitors": competitors,
        "strengths": keep_source_metrics(analysis.competitor_analysis.strengths),
        "opportunities": keep_source_metrics(analysis.competitor_analysis.opportunities),
        "competitive_advantages": keep_source_metrics(analysis.competitor_analysis.competitive_advantages),
    })
    if numerical_removed:
        notices.append(
            f"Removed {numerical_removed} quantified competitive claims not present in fetched source; "
            "claims quoted by the source are still not independently verified"
        )
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
