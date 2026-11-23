# Dxora v1.3 — consolidated quality fixes (23 November 2026)

**Scope:** fixes identified while reviewing saved Jira, Shopify and HubSpot outputs. This is an **offline-tested patch**, not a claim of deployed v1.3 success. No external search or paid research provider.

1. Remove ambiguous/placeholder/numbered competitors (including the observed `Salesforce (Competitor 2 placeholder / Freshworks)`), brand-as-competitor entries and duplicate aliases. Missing peers stay missing rather than being fabricated.
2. Keep source evidence URLs/excerpts tied to exact literal mentions already extracted from the submitted page; preserve `unverified_suggestion` for other peers. Source mentions do not validate strengths, market metrics or business claims.
3. Remove unsupported quantified claims from competitive assertions when the numbers are absent from extracted page text. **First-party page claims can still be inaccurate.** Non-numeric marketing claims still require human review.
4. Add distinctness checks for exactly five search queries and five services. Bad responses fail validation rather than returning a superficially successful result.
5. Refuse empty website HTML and enforce exact MIME type matching (fixes `application/octet-stream; filename="text/html"`).
6. Fix offline reference matching for known-company homepages; warn about placeholders, duplicate names, source-label inconsistencies and numerical assertions. Don't present an offline heuristic as measured factual accuracy.
7. Isolate process-wide limiter state in tests, avoiding test-order-dependent 429 failures. Production limiter is unchanged.
8. Preserve all existing 60 tests; **74 offline tests passed** in the development environment.

**Unresolved external limits:** Gemini provider 429/quota cannot be bypassed by application code; no independent online competitor fact-checking; dynamic JS-only site data may be incomplete; per-process demo limiter is not multi-instance durable; factual accuracy has not been numerically benchmarked.

**Deployment verification (23 November 2026):** The applicant ran 74/74 local offline tests, pushed commit `d9ddb03` to public GitHub `main`, and confirmed Render marked that commit **Live**. The public `/health` response returned `{'status':'ok','version':'1.3.0'}`. Cropped screenshots are included under `evidence/`. No new v1.3 full analysis POST has been asserted or performed as part of this verification. No submission email has been sent.

## 23 November 2026 — research documentation addendum

Independent web research was carried out for the three already analyzed companies: three Jira alternatives, four Shopify alternatives and three HubSpot alternatives (10 entries). Each has official product documentation and editorial comparison context. The offline audit script reconciles captured real POST outputs without any additional Gemini API calls. Production FastAPI analysis logic is unchanged; research is not hidden as hard-coded LLM output and no new v1.3 POST is claimed.

This research/evidence addendum adds 6 offline tests, giving **80 passing tests in the review environment**. The applicant's previous Windows run of 74 tests remains valid for the earlier code release; the new 6 tests are independent read-only research assertions.
