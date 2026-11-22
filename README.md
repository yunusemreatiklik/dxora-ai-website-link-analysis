# AI-Powered Website Link Analysis API

**Python 3 · FastAPI · Pydantic · HTTPX · BeautifulSoup · Gemini REST API**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/) [![API](https://img.shields.io/badge/API-FastAPI-009688)](https://fastapi.tiangolo.com/)

FastAPI endpoint for real website HTML extraction, safe URL validation and **five-section, LLM-generated business intelligence**. Built against [Dxora Technologies' Link Analysis practical test](https://github.com/chivoxai/practical-test/blob/main/link-analysis.md).

**Status:** functional tested prototype with production-minded restrictions; public URL must be deployed separately. The README does not imply tests against OpenAI/Claude or independently verified competitor research.

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
   |      -> bounded retries for transient 429/5xx
   +-- Pydantic validates five analysis sections and exactly five queries/services
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
| `429` | Per-client limit, daily demo budget or concurrency guard |
| `502` | Website fetch or Gemini provider failed, or required JSON missing |
| `503` | Gemini API key is missing |

Gemini temporary `429/5xx` errors are retried **at most twice**, with short bounded delays. Unsupported models or invalid credentials do not silently fall back to fabricated data.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The offline suite covers URL validation, DNS rejection, **pinning the validated public IP for the connection while preserving Host/SNI**, redirect checks, HTML extraction, large bodies, model response contracts, Gemini errors, OpenAPI schema and demo limits. The original suite had 26 passing tests; v1.0 adds regression tests. **These tests use mocks and do not incur LLM API charges**. A separate real Jira response is captured under `evidence/`.

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
- [ ] Run optional actual three-model speed/schema benchmark and review factual grounding
- [ ] Add current screenshots/logs of local and deployed execution
- [ ] Deploy publicly; confirm `/docs` and `/link-analysis` work from outside localhost
- [ ] Record URLs and final chosen discussion time in the email to `hr@chivoxai.com`
- [ ] Confirm company LinkedIn/CREST Instagram verification per assignment

No password, API key or personal credential should be committed to this repository.
