# v1.1 quality release — source-aware, no invented competitive facts

- Real comparison cases: Jira, Shopify, HubSpot, researched source links (offline evaluation reference only).
- Prompt asks for three plausible peers for recognizable products, always labelled unverified unless mentioned by the source page. This cannot guarantee three names on every API call.
- Empty `brand.main_products_services` may be filled from source-labelled services **only when a distinctive service-name term is present in downloaded page content**. This is a consistency check, not factual external verification.
- Quality limitations expose missing competitor candidates, weak product evidence and duplicate SEO title/meta description. No synthetic competitor names and no additional LLM calls.
- Offline real-company evaluation CLI reports raw quality checks, not benchmark accuracy.
- Captured actual Render Jira v1.0 response is included unaltered as baseline evidence.
- README, three-model benchmark overview, evidence notes and version `/health` bumped to `1.1.0`.

## Before deployment

1. `python -m pytest -q` — 41 offline tests passed in the packager's environment.
2. Check `git status --short`, `git diff --check`; verify `.env` is still ignored.
3. Commit/push *only after review*. Render will then redeploy if auto-deploy is enabled.
4. Confirm `/health` 1.1.0 and rerun real Jira via Swagger; save JSON separately. Never represent v1.0 capture as v1.1 outcome.
5. Only then test Shopify and HubSpot, capture any 403/502 truthfully.

No email submission is part of this package.
