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

**Deployment:** Do not send a submission email, push to GitHub, or deploy to Render until the applicant has reviewed the patch and verified `pytest` on their own machine.
