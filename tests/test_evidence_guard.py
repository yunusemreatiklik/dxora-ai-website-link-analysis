"""Regression tests for untrusted model evidence fields (no real API calls)."""
import json
from pathlib import Path

from app.schemas import AIAnalysis, Competitor
from app.services.quality import improve_and_audit
from app.services.website_extractor import ExtractedWebsite

ROOT = Path(__file__).resolve().parent.parent


def fixture():
    payload = json.loads((ROOT / "evidence/jira-render-live-response.json").read_text(encoding="utf8"))
    page = ExtractedWebsite(
        final_url="https://www.atlassian.com/software/jira",
        title="Jira | Project Management for the AI Era | Atlassian",
        meta_description="Jira brings teams together with AI agents",
        headings=["Jira Project Management", "Rovo AI Search"],
        text="Jira project management software; Confluence integration and Teamwork Graph are tools.",
        characters_extracted=93,
    )
    ai = AIAnalysis.model_validate({"brand": payload["brand"], "analysis": payload["analysis"]})
    return page, ai


def test_website_service_gets_real_source_excerpt_and_url():
    page, ai = fixture()
    revised, _ = improve_and_audit(page, ai)
    service = revised.analysis.top_services[0]
    assert service.evidence_status == "website_content"
    assert service.evidence_url == page.final_url
    assert "Jira Project Management" in service.evidence_excerpt


def test_fabricated_service_evidence_is_not_accepted():
    page, ai = fixture()
    fake = ai.analysis.top_services[0].model_copy(update={
        "name": "Magical Unicorn Quantum Sync",
        "evidence_status": "website_content",
        "evidence_url": "https://fake-source.example/",
        "evidence_excerpt": "Fabricated testimonial",
    })
    ai = ai.model_copy(update={"analysis": ai.analysis.model_copy(update={
        "top_services": [fake, *ai.analysis.top_services[1:]],
    })})
    revised, notices = improve_and_audit(page, ai)
    service = revised.analysis.top_services[0]
    assert service.evidence_status == "inferred_suggestion"
    assert service.evidence_url is None and service.evidence_excerpt is None
    assert any("downgraded" in n for n in notices)


def test_single_generic_word_cannot_verify_composite_service_name():
    page, ai = fixture()
    fake = ai.analysis.top_services[0].model_copy(update={"name": "Enterprise Jira Oracle Infrastructure"})
    ai = ai.model_copy(update={"analysis": ai.analysis.model_copy(update={
        "top_services": [fake, *ai.analysis.top_services[1:]],
    })})
    revised, _ = improve_and_audit(page, ai)
    assert revised.analysis.top_services[0].evidence_status == "inferred_suggestion"


def test_fake_competitor_claimed_mention_downgraded():
    page, ai = fixture()
    fake = Competitor(
        name="FictionalSoft", main_service="work management",
        strengths=["Amazing"], weaknesses_or_gaps=["None"],
        evidence_status="mentioned_on_website", evidence_url="https://fake.example/",
        evidence_excerpt="A made-up sentence",
    )
    ai = ai.model_copy(update={"analysis": ai.analysis.model_copy(update={
        "competitor_analysis": ai.analysis.competitor_analysis.model_copy(update={"competitors": [fake]}),
    })})
    revised, notices = improve_and_audit(page, ai)
    got = revised.analysis.competitor_analysis.competitors[0]
    assert got.evidence_status == "unverified_suggestion"
    assert got.evidence_url is None and got.evidence_excerpt is None
    assert any("competitor source" in n for n in notices)


def test_real_competitor_name_mentioned_is_not_external_verification():
    page, ai = fixture()
    page = ExtractedWebsite(**{**vars(page), "text": page.text + " Jira versus Asana for team management."})
    candidate = Competitor(
        name="Asana", main_service="work management", strengths=["unknown"],
        weaknesses_or_gaps=["unknown"], evidence_status="mentioned_on_website",
        evidence_url="https://untrusted-source.example/", evidence_excerpt="invented excerpt",
    )
    ai = ai.model_copy(update={"analysis": ai.analysis.model_copy(update={
        "competitor_analysis": ai.analysis.competitor_analysis.model_copy(update={"competitors": [candidate]}),
    })})
    revised, notes = improve_and_audit(page, ai)
    got = revised.analysis.competitor_analysis.competitors[0]
    assert got.evidence_status == "mentioned_on_website"
    assert got.evidence_url == page.final_url
    assert "Asana" in got.evidence_excerpt
    assert "claims about features" in " ".join(notes)


def test_unverified_competitor_cannot_carry_proof_url_even_when_on_page():
    page, ai = fixture()
    page = ExtractedWebsite(**{**vars(page), "text": page.text + " Jira versus Asana."})
    candidate = Competitor(
        name="Asana", main_service="work management", strengths=["unknown"],
        weaknesses_or_gaps=["unknown"], evidence_status="unverified_suggestion",
        evidence_url="https://somewhere.example", evidence_excerpt="forged",
    )
    ai = ai.model_copy(update={"analysis": ai.analysis.model_copy(update={
        "competitor_analysis": ai.analysis.competitor_analysis.model_copy(update={"competitors": [candidate]}),
    })})
    revised, _ = improve_and_audit(page, ai)
    got = revised.analysis.competitor_analysis.competitors[0]
    assert got.evidence_status == "unverified_suggestion"
    assert got.evidence_url is None and got.evidence_excerpt is None


def test_unsubstantiated_brand_products_are_removed():
    page, ai = fixture()
    brand = ai.brand.model_copy(update={"main_products_services": ["Jira", "Quantum Magic Upgrade"]})
    ai = ai.model_copy(update={"brand": brand})
    revised, notices = improve_and_audit(page, ai)
    assert revised.brand.main_products_services == ["Jira"]
    assert any("Unsubstantiated brand" in n for n in notices)


def test_empty_pages_do_not_generate_evidence():
    page, ai = fixture()
    page = ExtractedWebsite(**{**vars(page), "title": "", "meta_description": "", "headings": [], "text": ""})
    revised, _ = improve_and_audit(page, ai)
    assert revised.brand.main_products_services == []
    assert all(s.evidence_status == "inferred_suggestion" for s in revised.analysis.top_services)


def test_unsupported_service_percentage_removed():
    page, ai = fixture()
    service = ai.analysis.top_services[0].model_copy(update={
        "main_benefit": "Guaranteed 100% market visibility",
        "description": "Supports project management",
    })

    ai = ai.model_copy(update={
        "analysis": ai.analysis.model_copy(update={
            "top_services": [service, *ai.analysis.top_services[1:]]
        })
    })

    revised, notes = improve_and_audit(page, ai)
    got = revised.analysis.top_services[0]

    assert "100%" not in got.main_benefit
    assert got.description == "Supports project management"
    assert any("numerical service claims" in n for n in notes)


def test_inferred_service_cannot_claim_customer_numbers():
    page, ai = fixture()
    service = ai.analysis.top_services[0].model_copy(update={
        "name": "Unverified Premium Service",
        "evidence_status": "inferred_suggestion",
        "description": "Trusted by 50000 customers",
        "main_benefit": "Supports customer engagement",
    })

    ai = ai.model_copy(update={
        "analysis": ai.analysis.model_copy(update={
            "top_services": [service, *ai.analysis.top_services[1:]]
        })
    })

    revised, _ = improve_and_audit(page, ai)
    got = revised.analysis.top_services[0]

    assert "50000" not in got.description
    assert got.evidence_status == "inferred_suggestion"
    assert got.main_benefit == "Supports customer engagement"
