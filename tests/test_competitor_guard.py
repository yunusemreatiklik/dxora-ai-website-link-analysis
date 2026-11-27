"""No LLM credentials, provider calls or external network needed."""
import json
from pathlib import Path

from app.schemas import AIAnalysis
from app.services.competitor_guard import clean_name, is_own_brand, same_entity
from app.services.quality import improve_and_audit
from app.services.website_extractor import ExtractedWebsite
from scripts.assess_real_company import assess

ROOT = Path(__file__).resolve().parent.parent


def get_hubspot():
    data = json.loads((ROOT / "tests/fixtures/hubspot-v1.2-known-bad.json").read_text(encoding="utf-8"))
    page = ExtractedWebsite(
        final_url=data["website"],
        title=data["source_summary"]["title"],
        meta_description=data["source_summary"]["meta_description"],
        headings=["Marketing Hub", "Sales Hub", "Service Hub", "Content Hub", "Smart CRM"],
        text="HubSpot Marketing Hub Sales Hub Service Hub Content Hub Smart CRM",
        characters_extracted=64,
    )
    ai = AIAnalysis.model_validate({"brand": data["brand"], "analysis": data["analysis"]})
    return page, ai


def test_hubspot_real_failure_is_rejected_without_inventing_a_replacement():
    page, ai = get_hubspot()
    reviewed, notices = improve_and_audit(page, ai)
    names = [c.name for c in reviewed.analysis.competitor_analysis.competitors]
    assert names == ["Salesforce", "Zendesk"]
    assert len(names) == 2
    assert any("placeholder" in n for n in notices)
    assert any("Fewer than three" in n for n in notices)
    assert all(c.evidence_status == "unverified_suggestion" for c in reviewed.analysis.competitor_analysis.competitors)


def test_duplicate_salesforce_aliases_removed():
    page, ai = get_hubspot()
    first = ai.analysis.competitor_analysis.competitors[0]
    repeated = first.model_copy(update={"name": "Salesforce CRM"})
    candidates = [first, repeated, *ai.analysis.competitor_analysis.competitors[2:]]
    ai = ai.model_copy(update={"analysis": ai.analysis.model_copy(update={
        "competitor_analysis": ai.analysis.competitor_analysis.model_copy(update={"competitors": candidates}),
    })})
    reviewed, notices = improve_and_audit(page, ai)
    assert [c.name for c in reviewed.analysis.competitor_analysis.competitors] == ["Salesforce", "Zendesk"]
    assert any("duplicate" in notice for notice in notices)


def test_filters_self_competitor():
    page, ai = get_hubspot()
    first = ai.analysis.competitor_analysis.competitors[0]
    self_competitor = first.model_copy(update={"name": "HubSpot"})
    ai = ai.model_copy(update={"analysis": ai.analysis.model_copy(update={
        "competitor_analysis": ai.analysis.competitor_analysis.model_copy(update={"competitors": [self_competitor, first]}),
    })})
    revised, notes = improve_and_audit(page, ai)
    assert len(revised.analysis.competitor_analysis.competitors) == 1
    assert revised.analysis.competitor_analysis.competitors[0].name == "Salesforce"
    assert any("self-competitor" in n for n in notes)


def test_accept_real_company_names_but_not_placeholder_or_ambiguous_strings():
    assert clean_name("monday.com") == "monday.com"
    assert clean_name("Microsoft Azure DevOps") == "Microsoft Azure DevOps"
    assert clean_name("Salesforce (Competitor 2 placeholder / Freshworks)") is None
    assert clean_name("Salesforce / Freshworks") is None
    assert clean_name("Competitor #3") is None
    assert clean_name("TBD") is None
    assert same_entity("Microsoft Azure DevOps", "Azure DevOps")
    assert same_entity("Wix eCommerce", "Wix eCommerce CRM")
    assert not same_entity("Google Ads", "Google Analytics")
    assert is_own_brand("HubSpot", "HubSpot Customer Platform")


def test_reference_case_matches_homepages_and_known_aliases():
    for filename, expected in [
        ("shopify-v1.1-local-response.json", "Shopify"),
        ("hubspot-v1.2-known-bad.json", "HubSpot Smart CRM"),
        ("jira-v1.1-local-response.json", "Atlassian Jira"),
    ]:
        target = ROOT / ("tests/fixtures" if filename == "hubspot-v1.2-known-bad.json" else "evidence") / filename
        review = assess(target)
        assert review["company_case"] == expected
    hub = assess(ROOT / "tests" / "fixtures" / "hubspot-v1.2-known-bad.json")
    assert any("placeholder" in n for n in hub["warnings"])


def test_no_external_api_changes_to_five_section_contract():
    page, ai = get_hubspot()
    reviewed, notices = improve_and_audit(page, ai)
    assert len(reviewed.analysis.target_search_queries) == 5
    assert len(reviewed.analysis.top_services) == 5
    assert len(reviewed.brand.main_products_services) == 5
    assert all(s.evidence_url == page.final_url for s in reviewed.analysis.top_services)


def test_unverified_numeric_brand_strength_removed():
    page, ai = get_hubspot()
    reviewed, notices = improve_and_audit(page, ai)
    assert not any("2,000+" in item for item in reviewed.analysis.competitor_analysis.strengths)
    assert any("quantified" in item for item in notices)


def test_numerical_claim_can_be_reported_as_first_party_mention_not_fact():
    page, ai = get_hubspot()
    page = ExtractedWebsite(**{**vars(page), "text": page.text + " Our integrations now exceed 2,000+ apps."})
    reviewed, _ = improve_and_audit(page, ai)
    assert any("2,000+" in item for item in reviewed.analysis.competitor_analysis.strengths)


def test_empty_html_causes_clear_error_instead_of_hallucinated_analysis():
    import pytest
    from app.services.website_extractor import WebsiteFetchError, parse_html
    with pytest.raises(WebsiteFetchError, match="no usable text"):
        parse_html("<html><body><script>ignore me</script></body></html>", "https://example.com/")


def test_duplicate_required_search_query_rejected_by_schema():
    from pydantic import ValidationError
    import pytest
    _, ai = get_hubspot()
    items = list(ai.analysis.target_search_queries)
    items[1] = items[0].model_copy()
    with pytest.raises(ValidationError, match="distinct queries"):
        from app.schemas import Analysis
        Analysis.model_validate(ai.analysis.model_dump() | {"target_search_queries": [x.model_dump() for x in items]})


def test_duplicate_required_service_name_rejected_by_schema():
    from pydantic import ValidationError
    from app.schemas import Analysis
    import pytest
    _, ai = get_hubspot()
    items = list(ai.analysis.top_services)
    items[2] = items[0].model_copy()
    with pytest.raises(ValidationError, match="distinct services"):
        Analysis.model_validate(ai.analysis.model_dump() | {"top_services": [x.model_dump() for x in items]})


def test_hubspot_response_parse_still_valid_before_heuristic_cleaning():
    _, ai = get_hubspot()
    assert len(ai.analysis.top_services) == 5
    assert len(ai.analysis.target_search_queries) == 5


def test_http_live_contract_sanitizes_hubspot_fixture(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.llm_service import LLMResult
    page, ai = get_hubspot()

    async def fake_fetch(_url):
        return page

    async def fake_analyze(_page):
        return LLMResult(ai, "gemini", "mock-offline", {"input_tokens": 1, "output_tokens": 1})

    monkeypatch.setattr("app.main.fetch_website", fake_fetch)
    monkeypatch.setattr("app.main.analyze_with_gemini", fake_analyze)
    client = TestClient(app)
    assert client.get("/health").json()["version"] == "1.4.0"
    response = client.post("/link-analysis", json={"url": "https://www.hubspot.com"})
    assert response.status_code == 200
    body = response.json()
    assert [c["name"] for c in body["analysis"]["competitor_analysis"]["competitors"]] == ["Salesforce", "Zendesk"]
    assert any("placeholder" in limitation for limitation in body["limitations"])
    assert not any("2,000+" in x for x in body["analysis"]["competitor_analysis"]["strengths"])
    assert len(body["analysis"]["target_search_queries"]) == 5
    assert len(body["analysis"]["top_services"]) == 5


def test_fake_html_content_type_is_rejected_without_llm(monkeypatch):
    import asyncio
    import httpx
    from app.services.website_extractor import UnsupportedContent, fetch_website
    import pytest

    async def public(_url):
        return "93.184.215.14"

    monkeypatch.setattr("app.services.website_extractor.require_public_website", public)

    async def go():
        transport = httpx.MockTransport(lambda r: httpx.Response(
            200, headers={"content-type": 'application/octet-stream; filename="text/html"'},
            content=b"<h1>Wrong declared MIME</h1>"))
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(UnsupportedContent):
                await fetch_website("https://example.com", client=client)

    asyncio.run(go())
