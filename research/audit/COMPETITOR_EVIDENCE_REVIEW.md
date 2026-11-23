# Competitor evidence review — 23 November 2026

**Scope:** 3 real saved POST outputs (older versions) cross-checked against 10 manually researched alternatives. This is **not** new Gemini execution and not proof of generic live competitor search.

**Evidence rule:** Official product documentation supports product identity and stated capabilities; 2026 editorial comparison pages provide category-overlap context. Neither proves superiority, conversion uplift, pricing advantage or market share.

## Jira (Atlassian) — Software issue tracking / work management

Recorded real POST: `evidence/jira-v1.1-local-response.json`; original version (not v1.3).
Model's observed names: Asana, Monday.com, Microsoft Azure DevOps.
**Research match:** 3 existing names matched against 3 researched candidates.

| Real competitor | Officially documented capability | Official source | Independent/editorial context |
|---|---|---|---|
| Asana | Projects, portfolios, multi-team work and tasks | [Product reference](https://asana.com/features/project-management) | [Comparison context](https://zapier.com/blog/jira-alternatives/) |
| monday.com | Customizable project boards, status tracking and workflows | [Product reference](https://support.monday.com/hc/en-us/articles/360014437599-Project-management-with-monday-com) | [Comparison context](https://www.techrepublic.com/article/monday-com-vs-jira/) |
| Azure DevOps (Azure Boards) | Backlogs, work items, boards and sprint planning | [Product reference](https://learn.microsoft.com/en-us/azure/devops/boards/get-started/what-is-azure-boards) | [Comparison context](https://www.moveworkforward.com/blog/azure-devops-vs-jira) |

Scope distinctions (review questions, **not** tested weaknesses):

- **Asana:** Cross-functional project management emphasis versus Jira software issue-tracking workflows; compare actual agile needs and plans.
- **monday.com:** General work-management emphasis versus engineering-specific Jira workflows; test configuration and plan requirements.
- **Azure DevOps (Azure Boards):** Closest comparison is Azure Boards versus Jira issue tracking, not a complete feature-by-feature equivalence of Azure DevOps and Jira.

## Shopify — E-commerce platforms

Recorded real POST: `evidence/shopify-v1.1-local-response.json`; original version (not v1.3).
Model's observed names: WooCommerce, Squarespace, Wix eCommerce.
**Research match:** 3 existing names matched against 4 researched candidates.

| Real competitor | Officially documented capability | Official source | Independent/editorial context |
|---|---|---|---|
| WooCommerce | WordPress-based open-source commerce and control over store setup | [Product reference](https://woocommerce.com/download/) | [Comparison context](https://zapier.com/blog/shopify-alternatives/) |
| Squarespace Commerce | Store pages and physical/digital products or services selling | [Product reference](https://support.squarespace.com/hc/en-us/articles/206779077-Sell-on-Squarespace) | [Comparison context](https://zapier.com/blog/shopify-alternatives/) |
| Wix eCommerce | Template/AI website creation, product catalog, checkout and payments | [Product reference](https://www.wix.com/ecommerce/online-store) | [Comparison context](https://zapier.com/blog/shopify-alternatives/) |
| BigCommerce | Storefront, checkout, payments, multistorefront, SEO tools | [Product reference](https://www.bigcommerce.com/product/) | [Comparison context](https://zapier.com/blog/shopify-alternatives/) |

Scope distinctions (review questions, **not** tested weaknesses):

- **WooCommerce:** WordPress-based implementation and hosting responsibilities versus a hosted Shopify experience; real total cost depends on requirements.
- **Squarespace Commerce:** Design- and content-led site builder versus commerce-first platform; feature comparisons require plan checks.
- **Wix eCommerce:** Site-builder focus alongside commerce; compare large-catalog and customization needs, not unsupported performance claims.
- **BigCommerce:** Additional independently researched alternative not present in the saved Shopify POST; do not retroactively insert it into the historical response.

**Important:** BigCommerce is a fourth independently researched alternative, not a name present in the saved Shopify JSON. The real API output was NOT edited.

## HubSpot — Customer platform / CRM

Recorded real POST: `tests/fixtures/hubspot-v1.2-known-bad.json`; original version (not v1.3).
Model's observed names: Salesforce, Salesforce (Competitor 2 placeholder / Freshworks), Zendesk.
**Research match:** 1 existing names matched against 3 researched candidates.

| Real competitor | Officially documented capability | Official source | Independent/editorial context |
|---|---|---|---|
| Salesforce Sales Cloud | Lead, account, contact and opportunity management | [Product reference](https://www.salesforce.com/sales/cloud/) | [Comparison context](https://zapier.com/blog/hubspot-alternatives/) |
| Zoho CRM | Sales-force automation and sales funnel workflows | [Product reference](https://www.zoho.com/crm/features.html) | [Comparison context](https://zapier.com/blog/hubspot-alternatives/) |
| Pipedrive | Visual customizable sales pipeline, deal tracking and workflow automation | [Product reference](https://www.pipedrive.com/en/features/pipeline-management) | [Comparison context](https://zapier.com/blog/hubspot-alternatives/) |

Scope distinctions (review questions, **not** tested weaknesses):

- **Salesforce Sales Cloud:** Enterprise-oriented CRM capabilities versus HubSpot combined marketing/sales/service platform; total cost and complexity require independent plan testing.
- **Zoho CRM:** Sales process and CRM automation emphasis; do not assume feature or price advantage without edition comparison.
- **Pipedrive:** More focused on sales pipelines than the full HubSpot cross-function suite; not proof of superiority/inferiority.

**Rejected LLM draft name (not a researched company):** Salesforce (Competitor 2 placeholder / Freshworks).

**Other historical model candidates:** Zendesk. Not automatically fake; simply outside this narrow comparison set.

## Honest limits

- All saved POSTs are real recorded requests from earlier releases. `v1.3` Render **Live** and `/health` **1.3.0** were separately evidenced; a fresh v1.3 POST is NOT claimed. Do not repeat earlier POSTs merely to inflate the evidence count.
- The researched catalog is manually curated and versioned; the deployed generic endpoint does not automatically use these sources or perform external search. This is research evidence for the practical-test competitor section, not a claim of automatic factual grounding.
- Product capabilities may vary by plan. Do not convert source documentation into fabricated negative competitor weaknesses.
- If the evaluator requires current external research for every arbitrary submitted domain, that is a separate integration requiring a search provider and runtime validation; it is not silently solved here.

## Reproducible audit (offline, no quota)

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_researched_competitors --output research/audit
```

Output: one `audit-summary.json` and this Markdown report. Both preserve source version provenance.
