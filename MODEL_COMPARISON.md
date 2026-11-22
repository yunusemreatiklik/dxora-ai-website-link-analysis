# Model selection, measured evidence and API cost

Last checked: **20 November 2026**. All USD numbers are **standard paid-tier published prices per 1 million text tokens** (not an actual invoice). Prices and model availability can change.

## Three-provider comparison

| Provider/model | Input USD/1M | Output USD/1M | Input context | Structured JSON strategy | Quality/latency status | Suitability |
|---|---:|---:|---|---|---|---|
| **Google Gemini 3.5 Flash-Lite** (`gemini-3.5-flash-lite`) | **$0.30** | **$2.50** | Up to ~1M tokens (provider model limits apply) | `generationConfig.responseMimeType=application/json`, then Pydantic validation | **Real Jira run passed** (1,656 in / 1,236 out). Latency not recorded in that run. | **Chosen**: working API, structured results, economical input processing |
| **OpenAI GPT-5 mini** (`gpt-5-mini`) | **$0.25** | **$2.00** | 400,000 tokens | JSON schema / structured output API, validate with Pydantic | **Not tested with a live OpenAI key**. No speed/quality score claimed. | Strong alternative where OpenAI credentials are available |
| **Anthropic Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) | **$1.00** | **$5.00** | 200,000 tokens | tool input schema / strict response strategy plus Pydantic | **Not tested with a live Anthropic key**. No speed/quality score claimed. | Alternative for high-quality text and structured tool workflows |

Official sources (review prices again before submitting):

- Google: https://ai.google.dev/gemini-api/docs/pricing
- Google model reference: https://ai.google.dev/gemini-api/docs/models
- OpenAI GPT-5 mini: https://developers.openai.com/api/docs/models/gpt-5-mini
- Anthropic: https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic model reference: https://platform.claude.com/docs/en/models/haiku-4-5/overview

**Important:** This is a source-based price/context/feature comparison, **not a measured cross-provider speed or accuracy benchmark**. The take-home allows a comparison of at least three models or providers; benchmarked metrics must be distinguished from estimates.

## Observed real analysis — Jira

A real Google Gemini run against `https://www.atlassian.com/software/jira` returned `HTTP 200`, `analysis_complete`, all five sections and valid JSON. The captured response is in `evidence/jira-live-response.json`.

- Model: `gemini-3.5-flash-lite`
- Input tokens **1,656** (measured, API response)
- Output tokens **1,236** (measured, API response)
- Total tokens **2,892** (measured, API response)
- Gemini 3.5 Flash-Lite standard paid-tier **estimated API cost**: `(1656 * 0.30 + 1236 * 2.50)/1,000,000 = $0.0035868`.
- Actual billed cost is **not known**; free tiers and billing status matter.
- **Response latency:** not collected in v0.3. The v1.0 API reports `response_seconds` for future actual runs.
- **Accuracy:** no independently labeled benchmark exists; competitors are labeled unverified unless evidenced on the submitted page.

The Jira output includes three *suggested* competitors and five services. Asana, Monday.com and Azure DevOps were not separately verified by a web-search tool. The response records `unverified_suggestion` for each.

## Reproducible three-model Gemini benchmark

Use one API key and the **same** three websites for three Gemini models: 3.5 Flash-Lite, 3.1 Flash-Lite and 3.5 Flash. This offers an additional within-provider model comparison using actual timing, token usage and JSON validity rather than guessed numbers.

```powershell
# From the project root; inspect API quota/billing before running.
.\.venv\Scripts\python.exe -m scripts.benchmark_gemini --live
```

By default, this issues up to **nine live model calls**. It writes `benchmarks/results.csv`, containing each model/site's `http_llm_seconds`, schema success, token usage and price estimate. **Results are not included until run** (the tool must not fabricate benchmark findings). CSV and the detailed generated JSON snapshots in `benchmarks/sample_outputs/` are ignored by Git; use them to manually compare source-grounding, and publish only reviewed non-sensitive summaries.

For an unbiased human evaluation, review each generated response against the page HTML on these dimensions: correct brand identity, service evidence status, useful/realistic queries, competitor claims marked as unverified, SEO specificity and target-audience specificity. Track scores separately from schema validation. The evaluation needs documented rubrics and human scoring, not an invented 'accuracy %'.

## Expected speed and accuracy (not fabricated)

The existing Jira proof does **not** include elapsed time. For planning only, the application's typical successful end-to-end time can be expected in a range of **roughly 10–60 seconds** depending on source HTML, model load and network. **This is a rough engineering estimate, not measured latency or a service-level agreement.** Actual timings are captured by the script and returned in `model_info.response_seconds` for future runs. The code has a 60-second HTTP timeout per attempt and up to two retries, so worst-case error paths may take longer.

Qualitative accuracy: the Jira sample identifies the correct brand and produces all five expected sections, but competitor descriptions are unverified model suggestions. Neither this nor passing schema checks establishes an independently benchmarked factual accuracy percentage.

## Token efficiency and recommendation

1. Strip scripts, navigation and redundant markup. Extract up to 15,000 cleaned characters, passing at most 12,000 characters to the model.
2. Limit LLM generation to 6,000 output tokens; temperature 0.15 supports consistency.
3. Use a low-cost model for routine website extraction/analysis; escalate only failed or high-complexity analyses.
4. Avoid automatic repeated calls beyond two retries on temporary errors; apply public demo request budgets.
5. Consider caching by URL + normalized content hash in a future production deployment. Do not cache changing sites indefinitely.
6. Choose **Gemini 3.5 Flash-Lite** as the deployed base because this user has completed a successful real run with a valid API key. **GPT-5 mini** is the alternative pending credentials and a matching benchmark.

Cost is only the model portion; network, hosting, taxes, external data and optional search grounding may add costs. Provider pricing, quota and throughput should be checked when deploying.
