"""Research source catalog integrity checks (offline, no Gemini or web access)."""
from pathlib import Path
from scripts.audit_researched_competitors import audit_case, find_researched_peer, load_catalog, render_markdown


def test_three_cases_and_ten_source_backed_competitors():
    cat=load_catalog()
    assert [c['key'] for c in cat['cases']] == ['jira','shopify','hubspot']
    assert sum(len(c['competitors']) for c in cat['cases']) == 10
    assert all(len(c['competitors'])>=3 for c in cat['cases'])


def test_saved_post_provenance_and_real_analysis_sections():
    data=load_catalog()
    for case in data['cases']:
        audit=audit_case(case)
        assert audit['saved_post_status']=='analysis_complete'
        assert audit['historical_post_not_v1_3'] is True
        assert audit['recorded_model'] == 'gemini-3.5-flash-lite'
        assert audit['researched_competitor_count']>=3


def test_hubspot_draft_name_rejected_but_real_competitors_documented():
    hub=load_catalog()['cases'][-1]
    audit=audit_case(hub)
    assert len(audit['bad_placeholder_names'])==1
    assert find_researched_peer('Salesforce (Competitor 2 placeholder / Freshworks)',hub) is None
    assert {'Salesforce Sales Cloud','Zoho CRM','Pipedrive'} == {p['name'] for p in hub['competitors']}


def test_shopify_matches_existing_real_post_no_retroactive_fabrication():
    shop=load_catalog()['cases'][1]
    report=audit_case(shop)
    assert {'WooCommerce','Squarespace Commerce','Wix eCommerce'}.issubset(set(report['matched_to_external_research']))
    assert 'BigCommerce' not in report['saved_observed_competitors']
    assert 'BigCommerce' in {p['name'] for p in shop['competitors']}


def test_jira_matches_real_observed_alternative_names():
    jira=load_catalog()['cases'][0]
    report=audit_case(jira)
    assert report['matched_observed_count']==3


def test_report_explicitly_rejects_claim_of_generic_live_research():
    cat=load_catalog()
    docs=render_markdown(cat,[audit_case(c) for c in cat['cases']])
    assert 'not a claim of automatic factual grounding' in docs
    assert 'a fresh v1.3 POST is NOT claimed' in docs
    assert 'not a name present in the saved Shopify JSON' in docs
