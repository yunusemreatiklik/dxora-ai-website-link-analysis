"""No actual Gemini requests: typed quality regression checks."""
import json
from pathlib import Path

from app.schemas import AIAnalysis
from app.services.quality import improve_and_audit
from app.services.llm_service import build_prompt
from app.services.website_extractor import ExtractedWebsite
from scripts.assess_real_company import assess

PROJECT = Path(__file__).resolve().parent.parent
JIRA = PROJECT / "evidence" / "jira-render-live-response.json"


def jira_example():
    sample = json.loads(JIRA.read_text(encoding="utf-8"))
    page = ExtractedWebsite(
        final_url=sample["website"],
        title=sample["source_summary"]["title"],
        meta_description=sample["source_summary"]["meta_description"],
        headings=["Jira AI project management", "Rovo AI search"],
        text="Jira project management software; Teamwork Graph, Rovo AI Search and Confluence integration.",
        characters_extracted=sample["source_summary"]["characters_extracted"],
    )
    ai = AIAnalysis.model_validate({"brand": sample["brand"], "analysis": sample["analysis"]})
    return page, ai


def test_real_jira_fixture_is_a_valid_pydantic_response():
    p, ai = jira_example()
    assert len(ai.analysis.target_search_queries) == 5
    assert len(ai.analysis.top_services) == 5


def test_source_matched_services_fill_missing_products_without_new_llm_call():
    page, ai = jira_example()
    revised, notices = improve_and_audit(page, ai)
    assert "Jira Project Management" in revised.brand.main_products_services
    assert len(revised.brand.main_products_services) > 0
    assert not revised.analysis.competitor_analysis.competitors
    assert any("No competitor" in note for note in notices)


def test_inferred_services_not_promoted_as_fact():
    page, ai = jira_example()
    services = [s.model_copy(update={"evidence_status": "inferred_suggestion"}) for s in ai.analysis.top_services]
    ai = ai.model_copy(update={"analysis": ai.analysis.model_copy(update={"top_services": services})})
    revised, notices = improve_and_audit(page, ai)
    assert revised.brand.main_products_services == []
    assert any("could not be reliably recovered" in n for n in notices)


def test_identical_seo_title_and_description_are_flagged():
    page, ai = jira_example()
    _, notices = improve_and_audit(page, ai)
    assert any("SEO title" in n for n in notices)
    assert any("meta description" in n for n in notices)


def test_prompt_requires_explicit_website_services_and_competitor_uncertainty():
    page, _ = jira_example()
    p = build_prompt(page)
    assert '"main_products_services"' in p
    assert "three REALISTIC direct" in p
    assert "unverified_suggestion" in p
    assert "DISTINCT" in p


def test_real_business_reference_cases_are_distinct_and_have_sources():
    cases = json.loads((PROJECT / "benchmarks" / "real_company_cases.json").read_text(encoding="utf-8"))["cases"]
    assert len(cases) == 3
    assert len({c["sector"] for c in cases}) == 3
    assert all(len(c["reference_competitors"]) >= 3 and c["research_url"].startswith("https://") for c in cases)


def test_existing_live_jira_response_reports_weak_fields():
    reviewed = assess(JIRA)
    assert reviewed["schema_valid"]
    assert reviewed["brand_products"] == 0
    assert reviewed["competitor_candidates"] == 0
    assert any("competitor" in warning for warning in reviewed["warnings"])
    assert not reviewed["factual_accuracy_scored"]
