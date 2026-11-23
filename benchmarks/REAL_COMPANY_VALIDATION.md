# Real company validation plan — 22 November 2026

This plan tests the **generic** FastAPI workflow against three real commercial products. The JSON reference catalog is for **human evaluation only**, not used to inject named companies into API replies. Never fake a successful HTTP status or pretend that model-suggested competitors were verified by this tool.

## Selected reference cases

| Company and real URL to POST | Sector | Known competitors for human cross-check | Source used to identify alternatives |
|---|---|---|---|
| **Jira** — `https://www.atlassian.com/software/jira` | Project management/SaaS | Asana, monday.com, Azure DevOps | [Atlassian comparison](https://www.atlassian.com/software/jira/comparison) (vendor-produced; not neutral) |
| **Shopify** — `https://www.shopify.com/online` | E-commerce | BigCommerce, WooCommerce, Wix | [Shopify comparison](https://www.shopify.com/compare) (vendor-produced) |
| **HubSpot Smart CRM** — `https://www.hubspot.com/products/crm` | CRM/sales and marketing | Salesforce, Zoho CRM, Pipedrive | [Zapier 2026 review](https://zapier.com/blog/hubspot-alternatives/) (editorial, with potential affiliate incentives) |

These are **research reference examples**. The live application does **not** fetch these research URLs, independently validate competitor features, or hard-code three names per domain. Unknown sites still use website extraction and Gemini analysis. A proposed competitor must be labelled `unverified_suggestion` unless explicitly named on the submitted website; strengths/weaknesses are suggestions, not verified market claims. A vendor's comparison page is evidence of naming, not a neutral adjudication of quality.

## Execution order after a code change

1. Run `python -m pytest -q` (offline, no Gemini key required). Record the actual count.
2. Deploy only after local tests succeed and Git changes are reviewed. Verify `/health` shows the **new** version and `/docs` is available.
3. Test `POST /link-analysis` with **Jira first** using Swagger; download the 200 JSON into `evidence/jira-render-v1.1-response.json`. If it fails, capture the sanitized error once and investigate before retrying. Do not burn free-tier quota with repeated calls.
4. Run `python -m scripts.assess_real_company evidence/jira-render-v1.1-response.json` locally. Look for >=3 plausible labelled competitors, non-empty on-page products/services, 5 queries, 5 services, relevant SEO suggestions, and meaningful target audiences. Independently judge whether competitor claims make sense.
5. Only after Jira works, test **Shopify**. Record HTTP status or a blocked-scraping limitation without bypassing the site's protections. Repeat for **HubSpot**. If these domains are inaccessible from Render, pick an accessible alternative and record the substitution; do not claim these tests passed.
6. Compare results against the catalog `benchmarks/real_company_cases.json` and fill `benchmarks/MANUAL_REVIEW_TEMPLATE.csv` **by human inspection**. Schema success is not factual accuracy.
7. Review token usage, `response_seconds`, extracted text length and factual grounding. Disclose warning messages in `limitations` for non-verified peers, repeated SEO, or weak source evidence.

## Current measured baseline (not a v1.1 claim)

The actual v1.0 **Jira** Render capture `evidence/jira-render-live-response.json` has a valid `analysis_complete` response, 5 queries, 5 services, `model_info.response_seconds=4.178`, 1,725 input tokens, 1,220 output tokens, **0 competitor candidates**, **0 brand products**, and recommended SEO title/meta description identical to the existing source. Thus it was *technically successful but content-incomplete*. The v1.1 change aims to improve these shortcomings, not to retroactively alter evidence.

## Quality boundary

The after-LLM `improve_and_audit` function may recover product names from model-labelled website services if distinctive service tokens also occur in the extracted HTML text. It never fills competitors from a canned list. It preserves empty competitors and unchanged SEO proposals as explicit limitation notices; this is preferable to presenting generated content as verified research. Further improvement would require a real, reliable search/competitor data API with source citations and budget controls.

## v1.3 review — actual saved outputs

- Jira and Shopify v1.1 examples were captured locally and stored with descriptive names under `evidence/`; reported 3 candidate peers each (not all claims sourced).
- HubSpot v1.2 **live** example originally returned HTTP 200 but mistakenly included `Salesforce (Competitor 2 placeholder / Freshworks)`. The original flawed response is retained as a known-bad fixture in `tests/fixtures/`, and v1.3 regression checks assert that this record is removed without creating an unverified replacement.
- The offline review command now matches a reference company by its homepage when the catalog has exactly one entry for that domain; it reports placeholder peers, duplicates, invalid evidence fields, repeated SEO and quantified claims. **This is not a third-party fact-checker.**

Review commands, **no API requests**:

```powershell
.\.venv\Scripts\python.exe -m scripts.assess_real_company tests/fixtures/hubspot-v1.2-known-bad.json
.\.venv\Scripts\python.exe -m pytest -q
```
