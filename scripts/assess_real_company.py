"""Offline review aide for live JSON; no network calls, no assumed factual accuracy.

Usage:
    python -m scripts.assess_real_company evidence/jira-render-live-response.json
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from app.schemas import LinkAnalysisResponse


CATALOG = Path(__file__).resolve().parent.parent / "benchmarks" / "real_company_cases.json"


def assess(response_path: Path) -> dict:
    data = json.loads(response_path.read_text(encoding="utf-8"))
    result = LinkAnalysisResponse.model_validate(data)
    cases = json.loads(CATALOG.read_text(encoding="utf-8"))["cases"]
    case = next(
        (c for c in cases if urlsplit(c["website"]).netloc.casefold() == urlsplit(result.website).netloc.casefold()
         and urlsplit(c["website"]).path.rstrip("/") == urlsplit(result.website).path.rstrip("/")),
        None,
    )
    analysis = result.analysis
    reference_names = {n.casefold() for n in case["reference_competitors"]} if case else set()
    proposed = analysis.competitor_analysis.competitors
    matched = [c.name for c in proposed if c.name.casefold() in reference_names]
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
    for competitor in proposed:
        if competitor.evidence_status == "unverified_suggestion" and competitor.evidence_url:
            warnings.append(f"{competitor.name}: unverified competitor should not claim evidence URL")
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
        "note": "Reference matches are cross-check aids, not proof of individual competitor claims.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess evidence from a real-company live API response")
    parser.add_argument("response", type=Path, help="Path to saved JSON response")
    args = parser.parse_args()
    try:
        print(json.dumps(assess(args.response), indent=2, ensure_ascii=False))
    except Exception as exc:
        parser.exit(1, f"Quality review could not parse response: {exc}\n")


if __name__ == "__main__":
    main()
