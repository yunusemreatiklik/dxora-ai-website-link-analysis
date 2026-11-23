"""Offline review aide for saved live analysis JSON; zero API calls.

This is a structure / plausibility checklist, NOT a factual accuracy benchmark.
Usage: python -m scripts.assess_real_company path/to/response.json
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from app.schemas import LinkAnalysisResponse
from app.services.competitor_guard import clean_name, same_entity, is_own_brand

CATALOG = Path(__file__).resolve().parent.parent / "benchmarks" / "real_company_cases.json"


def _hostname(url: str) -> str:
    return (urlsplit(url).hostname or "").casefold().removeprefix("www.")


def _path(url: str) -> str:
    return urlsplit(url).path.rstrip("/")


def _match_case(cases: list[dict], url: str) -> dict | None:
    exact = next((case for case in cases if _hostname(case["website"]) == _hostname(url)
                  and _path(case["website"]) == _path(url)), None)
    if exact:
        return exact
    # The company homepage is a legitimate benchmark of the same brand. Only
    # fall back if precisely one catalog entry is associated with this domain.
    domain_cases = [case for case in cases if _hostname(case["website"]) == _hostname(url)]
    if len(domain_cases) == 1 and _path(url) in ("", "/"):
        return domain_cases[0]
    return None


def assess(response_path: Path) -> dict:
    data = json.loads(response_path.read_text(encoding="utf-8"))
    result = LinkAnalysisResponse.model_validate(data)
    cases = json.loads(CATALOG.read_text(encoding="utf-8"))["cases"]
    case = _match_case(cases, result.website)
    analysis = result.analysis
    reference_names = case["reference_competitors"] if case else []
    proposed = analysis.competitor_analysis.competitors
    matched = [c.name for c in proposed if any(same_entity(c.name, name) for name in reference_names)]
    source_title = result.source_summary.title.strip().casefold()
    source_meta = result.source_summary.meta_description.strip().casefold()
    seo = analysis.seo_improvements
    warnings = []
    if not result.brand.main_products_services:
        warnings.append("main_products_services is empty")
    if len(proposed) < 3 and case:
        warnings.append("Fewer than 3 competitor candidates for a well-known commercial product")
    if seo.recommended_title.strip().casefold() == source_title:
        warnings.append("SEO title duplicates page title")
    if source_meta and seo.meta_description.strip().casefold() == source_meta:
        warnings.append("SEO description duplicates current description")
    seen: list[str] = []
    for competitor in proposed:
        if clean_name(competitor.name) is None:
            warnings.append(f"Invalid placeholder/ambiguous competitor: {competitor.name}")
        if is_own_brand(competitor.name, result.brand.name):
            warnings.append(f"Own brand suggested as competitor: {competitor.name}")
        if any(same_entity(competitor.name, previous) for previous in seen):
            warnings.append(f"Duplicate competitor: {competitor.name}")
        seen.append(competitor.name)
        if competitor.evidence_status == "unverified_suggestion" and (competitor.evidence_url or competitor.evidence_excerpt):
            warnings.append(f"{competitor.name}: unverified competitor should not claim source evidence")
        if competitor.evidence_status == "mentioned_on_website" and not (competitor.evidence_url and competitor.evidence_excerpt):
            warnings.append(f"{competitor.name}: missing source mention evidence")
    for service in analysis.top_services:
        if service.evidence_status == "website_content" and not (service.evidence_url and service.evidence_excerpt):
            warnings.append(f"{service.name}: website_content without source mention evidence")
    # Claims about counts/percentages are not independently sourced by this API.
    quantitative = []
    for claim in [*analysis.competitor_analysis.strengths,
                  *analysis.competitor_analysis.competitive_advantages,
                  *[s.main_benefit for s in analysis.top_services]]:
        if re.search(r"\b\d[\d,.]*\s*(?:\+|%|million\b|billion\b|apps\b|customers\b|integrations\b)|\b(?:hundreds|thousands|millions) of\b", claim, re.I):
            quantitative.append(claim)
    if quantitative:
        warnings.append(f"{len(quantitative)} quantitative claims need independent source review")
    return {
        "file": str(response_path),
        "company_case": case["company"] if case else "No matched reference case",
        "schema_valid": True,
        "queries": len(analysis.target_search_queries),
        "services": len(analysis.top_services),
        "brand_products": len(result.brand.main_products_services),
        "competitor_candidates": len(proposed),
        "reference_candidates_matched": matched,
        "warnings": warnings,
        "factual_accuracy_scored": False,
        "note": "This checks structure and flags suspicious output. Reference matches do NOT prove any factual competitor claim.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Review saved real-company analysis without network access")
    parser.add_argument("response", type=Path, help="Path to saved JSON response")
    args = parser.parse_args()
    try:
        print(json.dumps(assess(args.response), indent=2, ensure_ascii=False))
    except Exception as exc:
        parser.exit(1, f"Quality review could not parse response: {exc}\n")


if __name__ == "__main__":
    main()
