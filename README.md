# AI-Powered Website Link Analysis API

**Python 3 · FastAPI · Pydantic · HTTPX · BeautifulSoup · Gemini REST API**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/) [![API](https://img.shields.io/badge/API-FastAPI-009688)](https://fastapi.tiangolo.com/)

FastAPI endpoint for real website HTML extraction, safe URL validation and **five-section, LLM-generated business intelligence**. Built against [Dxora Technologies' Link Analysis practical test](https://github.com/chivoxai/practical-test/blob/main/link-analysis.md).

**Status:** **v1.3.0** (`d9ddb03`) was confirmed **Live** on Render on **23 November 2026**, and its public `/health` endpoint returned `{'status':'ok','version':'1.3.0'}` (see `evidence/screenshots/09-v1.3-render-live-d9ddb03.png` and `evidence/screenshots/10-v1.3-health.png`). **74 local offline tests passed.** The historical Jira/Shopify/HubSpot POST captures are real model API responses from earlier releases, each with `analysis_complete`, five search queries and five services. This documentation upgrade requires no new POST or Gemini usage. As of 23 November 2026, a **separate, manually source-checked competitor research pack** now covers the saved Jira, Shopify and HubSpot examples with official vendor documents and editorial comparisons (`research/audit/COMPETITOR_EVIDENCE_REVIEW.md`). This is **not an automatic external-search engine in the deployed API**; the LLM's historical response values have not been rewritten. No cross-provider live OpenAI/Anthropic benchmark is claimed.

**Latest validation - 27 November 2026**

- Release: v1.4.0
- Validated code commit: ac4066b
- Render deployment: successful
- Automated tests: 102 passed
- CREST official website: HTTP 200, analysis_complete
- Instagram: HTTP 200, analysis_limited
- LinkedIn restricted access: HTTP 422
- Private IP protection: HTTP 400
- Jira and Shopify: HTTP 200 in earlier v1.4 tests
- Search platform coverage: Google, Facebook, Instagram, LinkedIn and X
- CREST model response time: 5.043 seconds
- CREST token usage: 4299
- Primary provider: Gemini 3.5 Flash-Lite
- Optional fallback: mock-tested, disabled in production
- Source mentions are not independent factual verification.

**Live demo:** https://dxora-ai-link-analysis-rni5.onrender.com/docs

**Health:** https://dxora-ai-link-analysis-rni5.onrender.com/health


## Capabilities

1. **Competitor vs brand:** brand overview, strengths, competitive advantages, three suggested competitors when available, competitor gaps, positioning opportunities. Competitor names not evidenced in the source are explicitly marked `unverified_suggestion`.
2. **Five target queries:** exactly five relevant queries, each with platforms chosen from Google, Facebook, Instagram, LinkedIn and X, search intent, business relevance and target audience. No fabricated search-volume metrics.
3. **SEO improvement:** primary/secondary/long-tail keywords, SEO title, meta description and relevant supporting content.
4. **Five services:** evidence-labelled services with description, industry, target customer and benefit. Inferences explicitly marked `inferred_suggestion`.
5. **Target audiences:** primary/secondary audiences, industries, business types, customer needs, geographic focus, customer profiles and interests.

## Architecture

```text
POST /link-analysis
   |
   +-- Pydantic request URL validation
   +-- best-effort demo rate + daily budget + concurrency guards
   +-- URL validation -> public DNS IP -> pinned IP HTTPS connection
   |      -> redirect revalidation -> stream limit (5 MB decompressed HTML)
   |      -> BeautifulSoup content cleaning -> 12k-character model context
   +-- Gemini REST generateContent (application/json)
   |      -> bounded 5xx/timeout retries; 429 quota-aware handling
   +-- Pydantic validates five sections and five DISTINCT queries/services
   +-- deterministic competitor hygiene (no placeholders, aliases, self-comparisons)
   +-- source-name evidence guard; unsupported quantitative claims flagged/removed
   +-- typed JSON response with model token counts and response_seconds
```

Website content is untrusted input; it is delimited in the prompt and must not be treated as instructions.

### Repository layout

```text
app/main.py                       API, OpenAPI response_model and error mappings
app/schemas.py                    Pydantic analysis contracts
app/limits.py                     per-client rate, daily and concurrency demo guards
app/utils/validators.py           URL checks, public DNS address selection
app/services/website_extractor.py pinned-IP HTML fetch/redirect checks, text extraction
app/services/llm_service.py       Gemini client, prompt, JSON parse and retry
app/services/quality.py           source-name evidence gate and output filtering
app/services/competitor_guard.py  generic competitor-name checks and de-duplication
scripts/assess_real_company.py    offline real-response structure/review checker
scripts/benchmark_gemini.py       repeatable three-model live experiment
MODEL_COMPARISON.md               pricing, measured evidence, model recommendation
evidence/jira-live-response.json   captured real Jira success response
tests/                            offline unit and contract tests
render.yaml                       Render deployment configuration
.env.example                      settings template; real .env is gitignored
```

## Installation (Windows PowerShell)

```powershell
cd C:\Users\CASPER\dxora-link-analysis
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
code .env
```

Enter your own `GEMINI_API_KEY` inside `.env` (not inside source files). The default `GEMINI_MODEL=gemini-3.5-flash-lite` is the model successfully tested on Jira. The model ID can be changed for benchmarks without changing Python code.

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 4000 --reload
```

- Interactive OpenAPI UI: **http://127.0.0.1:4000/docs**
- Health: **http://127.0.0.1:4000/health**
- Endpoint: **POST http://127.0.0.1:4000/link-analysis**

Linux/macOS: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt` then run `uvicorn app.main:app --host 0.0.0.0 --port 4000`.

## Example request and response

```bash
curl -X POST http://127.0.0.1:4000/link-analysis \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.atlassian.com/software/jira"}'
```

Abbreviated example (full captured real response in [`evidence/jira-live-response.json`](evidence/jira-live-response.json)):

```json
{
  "success": true,
  "status": "analysis_complete",
  "website": "https://www.atlassian.com/software/jira",
  "brand": {"name": "Jira", "category": "Project Management Software", "summary": "..."},
  "analysis": {
    "competitor_analysis": {"brand_overview": "...", "competitors": [], "strengths": [], "opportunities": []},
    "target_search_queries": ["five validated query objects"],
    "seo_improvements": {"primary_keyword": "...", "secondary_keywords": [], "recommended_title": "...", "meta_description": "...", "supporting_content": []},
    "top_services": ["five evidence-labelled service objects"],
    "target_audience": {"primary_audience": [], "secondary_audience": [], "industries": [], "customer_needs": []}
  },
  "model_info": {"provider": "gemini", "model": "gemini-3.5-flash-lite", "token_usage": {"input_tokens": 1656, "output_tokens": 1236, "total_tokens": 2892}},
  "source_summary": {"title": "Jira | Project Management for the AI Era | Atlassian", "characters_extracted": 4609},
  "limitations": ["..." ]
}
```

> This shortened excerpt is explanatory, not an exact complete schema. Use `/docs` or the evidence JSON for the full response.

## Failure behavior

| Error | Meaning |
|---|---|
| `400` | Invalid/unsafe URL, local or private host, disallowed port, blocked DNS result |
| `413` | More than 5 MB decompressed HTML |
| `415` | Non-HTML resource |
| `422` | Pydantic request validation failed |
| `429` | Per-client/demo rate limit **or Gemini model quota / upstream throttling**; upstream retry hint propagated when provided |
| `502` | Website fetch error, invalid LLM JSON, or non-transient provider configuration error |
| `503` | Gemini API key missing, or transient Gemini service/network failure after retries |
| `504` | Gemini request timed out after bounded retries |

For upstream **429**, the application returns HTTP 429 rather than masking it as 502. It parses Google's structured `QuotaFailure` / `RetryInfo` metadata (never echoes Google's raw error message), avoids retrying a known daily-quota failure, and only retries once when the provider explicitly suggests a delay of **three seconds or less**. The `Retry-After` response header is forwarded when available. Upstream 5xx/timeouts are retried at most twice with a short **1s/2s exponential backoff**. This improves transparency; it **cannot** raise Google free-tier quotas or guarantee successful requests during provider overload. Auto-switching models is intentionally disabled to avoid unexpected API usage and inconsistent results.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The offline suite covers URL validation, DNS/IP pinning and Host/SNI, redirect checks, MIME type / empty HTML rejection, extraction size guards, duplicate queries/services, LLM parsing, Gemini error handling, competitor placeholders/duplicates, and source-name evidence rules. **74 offline tests passed in the applicant's local Windows environment** before the successful v1.3 GitHub push and Render deploy. These unit tests do not establish that every live LLM output is factually correct. Mocks are used; **no Gemini API quota or paid APIs are consumed by these tests**.

## LLM model comparison and optimization

See **[MODEL_COMPARISON.md](MODEL_COMPARISON.md)** for the source-based comparison of Google Gemini 3.5 Flash-Lite, OpenAI GPT-5 mini and Anthropic Claude Haiku 4.5; **provider pricing**, context sizes, structured JSON approach, model choice and cost formula. The Jira test observed 1,656 input and 1,236 output tokens, estimated paid-tier cost **$0.0035868** at current Gemini 3.5 Flash-Lite prices. It was not a measured latency or benchmarked accuracy score.

`python -m scripts.benchmark_gemini --live` executes up to nine optional **real** Gemini calls on three models and three websites, reporting observed latency, schema validity and token consumption. This may use quota or incur charges. Accuracy requires a separate manual, source-grounded evaluation. Do not represent source-based estimates as measured results.

## Render deployment

1. Push the complete project to a **public GitHub repository**.
2. In Render: **New → Blueprint**, connect the repository and inspect `render.yaml`. If the `free` plan is unavailable in your account, select an available compatible plan. Do not deploy with the local dev `--reload` flag.
3. Set `GEMINI_API_KEY` under Render environment variables, not in GitHub. Set `GEMINI_MODEL=gemini-3.5-flash-lite` (or an available exact model ID).
4. Deploy and verify `https://<your-service>.onrender.com/health` and `/docs`.
5. Run an actual `POST https://<your-service>.onrender.com/link-analysis` request, verify all five sections and capture redacted evidence before submission.
6. Record the real deployment base URL and Swagger URL in the final submission; do not present localhost as public.

**Important deployment caveat:** demo quotas are per-process, held in memory, and reset on process restart; they are not strong billing protection across replicas. For long-term public production, add a shared Redis limiter, per-customer auth, provider-level spending quotas, bounded outbound egress and monitoring. IP-pinning plus Host/SNI is designed to stop DNS-rebinding in the fetch path, but does not replace defense in depth on the hosting network. Remote sites may block scraping or require JavaScript; this service deliberately does not bypass such restrictions.

## Submission checklist

- [x] FastAPI endpoint, five sections and actual Gemini response
- [x] Typed request/response models and offline regression tests
- [x] Published source-model pricing and justified cost choice
- [x] Recorded real Jira response (tokens/analysis)
- [x] Run 3-model/3-website live speed/schema benchmark (7/9 passed; factual grounding review remains separate)
- [x] Add deployment and `/health` screenshots for v1.3 (`evidence/render-v1.3-*.png`); older POST response evidence is labelled with its actual release
- [x] Deploy v1.3 (`d9ddb03`) publicly and verify its `/health` response is `1.3.0`; older v1.2 HubSpot POST evidence is retained as a known-bad fixture
- [x] Run 74 local tests and verify live v1.3 `/health` (fresh v1.3 `/link-analysis` POST not yet performed; do not claim it passed)
- [ ] Record URLs and final chosen discussion time in the email to `hr@chivoxai.com`
- [ ] Confirm company LinkedIn/CREST Instagram verification per assignment

No password, API key or personal credential should be committed to this repository.

## Source-backed competitor research — 23 November 2026

The applicant already captured **three genuine POST analysis outputs** (`Jira`, `Shopify`, `HubSpot`) on earlier versions, with five services and five search queries per result. They must not be dismissed as absent or misrepresented as a fresh v1.3 POST.

A reproducible **external-source competitor audit** now documents **3 Jira peers, 4 Shopify alternatives and 3 HubSpot peers (10 total)**. The research file `research/VERIFIED_COMPETITORS_2026-11-23.json` includes an **official product/help source** for each peer and independent/editorial comparison context, plus careful scope distinctions instead of untested negative claims. Exact historical model names are preserved for audit. The malformed HubSpot placeholder is explicitly rejected; three credible alternatives are separately documented, not fabricated into the saved model response.

- [Read the full source-backed comparison](research/audit/COMPETITOR_EVIDENCE_REVIEW.md)
- [Machine-readable source catalog](research/VERIFIED_COMPETITORS_2026-11-23.json)
- [Offline evidence audit result](research/audit/audit-summary.json)

Re-run evidence reconciliation **offline, without a model call**:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_researched_competitors --output research/audit
```

This is **manual source research** for three submitted domains, not dynamic internet fact-checking of every possible website. Official product materials corroborate advertised offerings but not performance superiority; editorial comparisons can have commercial incentives. The live generic LLM endpoint remains non-hardcoded.

## Real-company evaluation and v1.1 quality guard

The project was tested against a **real commercial Jira page on Render**: `evidence/jira-render-live-response.json` records a valid five-section response in **4.178 seconds** of Gemini processing (1,725 input / 1,220 output tokens). The snapshot also exposed shortcomings: zero suggested competitors, empty `brand.main_products_services`, and SEO fields copying the existing title and description. The capture is retained transparently instead of pretending those issues never happened.

In v1.1, the prompt explicitly asks for three **plausible real market peers** for identifiable commercial products, but labels them as `unverified_suggestion` where external evidence is absent. It does not require the model to hallucinate competitors for generic sites. Source-labelled services may populate an empty brand product list **only when their names share distinctive terms with the fetched website**; the limitation field explains the derivation. Unchanged SEO titles/descriptions and missing competitors are reported as quality notices, not silently replaced with made-up content. No extra LLM request is made for this quality check.

This is not a competitor-search API. The three researched comparison cases are **offline evaluation references**, never hard-coded API responses: Jira (project management), Shopify (e-commerce), and HubSpot (CRM). Their sources and review guidance are in [`benchmarks/REAL_COMPANY_VALIDATION.md`](benchmarks/REAL_COMPANY_VALIDATION.md). Some sites may block scraping; a 502 for that reason must be reported honestly.

Review a saved live JSON response **without any API key or network call**:

```powershell
.\.venv\Scripts\python.exe -m scripts.assess_real_company evidence/jira-render-live-response.json
```

The original Jira capture is expected to report quality warnings. Separately reviewed v1.1 Jira and Shopify outputs are retained as labelled examples in `evidence/`; a **known-bad v1.2 HubSpot response** is kept ONLY in `tests/fixtures/` to prevent recurrence of a real placeholder bug. Passing offline tests does not establish factual accuracy or guarantee that future LLM calls will succeed.


## v1.2 conservative source-evidence gate (offline, no search provider)

The optional `evidence_url` and `evidence_excerpt` fields in service and competitor
objects are filled **by deterministic code from the already fetched HTML text**
when the **entire name** appears, not by trusting a model-proposed citation.
If a service is marked `website_content` without an exact name mention, it is
downgraded to `inferred_suggestion`. A competitor marked `mentioned_on_website`
without a name mention is downgraded to `unverified_suggestion` and its evidence
URL/excerpt is removed. Unverified competitor candidates are still allowed
under the original assessment specification. `brand.main_products_services`
is filtered against actual page mentions.

**Scope:** Name-mention evidence does **not** prove service benefits, competitor
strengths or weaknesses, sales numbers, rankings, legal claims or pricing. This
release does **not** implement independent external competitor research, Tavily,
or any paid additional APIs. The resulting JSON accurately distinguishes what
we can and cannot substantiate from the supplied web page. Do not call this
full fact-checking. Run `python -m pytest -q` before deploying.


## v1.3 — output integrity and offline review (deployed; health verified)

- Reject placeholders and ambiguous competitor names such as `Salesforce (Competitor 2 placeholder / Freshworks)`; filter repeated aliases and a brand listed as its own competitor. **Never fill missing competitors with invented names.**
- Keep numeric competitive claims only when the exact numeric expression is present in the submitted website's extracted text. A source mention is **not third-party fact verification**.
- Reject duplicated target queries or top-service names at Pydantic validation rather than silently claiming five distinct results.
- Reject HTML that has no usable text/metadata and content types that merely *contain* `text/html` as a filename parameter.
- Match real-company reference cases by exact path or unambiguous homepage, including Shopify and HubSpot. Flag placeholders, repeated competitors, invalid evidence and quantitative claims for human review.
- See [`V1_3_CHANGELOG.md`](V1_3_CHANGELOG.md); tests use the actual previously captured **bad HubSpot response** as a regression fixture. No new LLM calls and no extra third-party API dependency.

### Published v1.3 demo (23 November 2026)

- Base URL: https://dxora-ai-link-analysis-rni5.onrender.com
- Health: https://dxora-ai-link-analysis-rni5.onrender.com/health
- Swagger: https://dxora-ai-link-analysis-rni5.onrender.com/docs
- Endpoint: `POST https://dxora-ai-link-analysis-rni5.onrender.com/link-analysis`

The live v1.3 `/health` response was confirmed; genuine earlier release POST captures are retained with their correct provenance. No duplicate live analysis call was needed for this documented research audit. Free Render instances sleep when idle; free Gemini quotas can produce `429`, which is reported rather than bypassed. This demo is not a guaranteed always-available production SLA.
