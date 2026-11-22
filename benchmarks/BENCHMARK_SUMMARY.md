# Dxora Link Analysis — Live Gemini Benchmark Results

**Measured on:** 20 November 2026
**Test scope:** Three publicly accessible URLs × three Google Gemini model IDs = **9 attempts**.
**Method:** The project's `python -m scripts.benchmark_gemini --live` script, which extracts each page once and submits the same extracted page to all three models. The reported latency is `http_llm_seconds` (model request, excluding website fetching). `estimated_paid_usd` is the script's token-price estimate, **not an invoice**.

## Complete per-request observations

| Page | Model | Outcome | Measured Gemini time (seconds) | Calculated API cost (USD) |
|---|---|---|---:|---:|
| Atlassian Jira | Gemini 3.5 Flash-Lite | **Failed** (`LLMServiceError`) | Not reported | Not reported |
| Atlassian Jira | Gemini 3.1 Flash-Lite | JSON validated | 7.940 | 0.00357125 |
| Atlassian Jira | Gemini 3.5 Flash | JSON validated | 22.447 | 0.01656750 |
| Python.org | Gemini 3.5 Flash-Lite | JSON validated | 5.198 | 0.00413250 |
| Python.org | Gemini 3.1 Flash-Lite | **Failed** (`LLMServiceError`) | Not reported | Not reported |
| Python.org | Gemini 3.5 Flash | JSON validated | 25.532 | 0.01587450 |
| Example.com | Gemini 3.5 Flash-Lite | JSON validated | 2.919 | 0.00221310 |
| Example.com | Gemini 3.1 Flash-Lite | JSON validated | 4.142 | 0.00193725 |
| Example.com | Gemini 3.5 Flash | JSON validated | 41.341 | 0.01079550 |

## Model-level summaries

| Model | Valid structured analyses / attempts | Success rate in this small sample | Mean response time (successful requests only) | Mean calculated cost (successful requests only) |
|---|---:|---:|---:|---:|
| Gemini 3.5 Flash-Lite | 2 / 3 | 66.7% | 4.059 s | $0.00317280 |
| Gemini 3.1 Flash-Lite | 2 / 3 | 66.7% | 6.041 s | $0.00275425 |
| Gemini 3.5 Flash | 3 / 3 | 100% | 29.773 s | $0.01441250 |

**Overall:** 7/9 model–URL pairs succeeded (**77.8%**). Seven reported successful calls account for **$0.05509160** in *calculated standard paid-tier cost*, not necessarily actual charges. Failed calls were not included in this cost total because token consumption was not reported.

## How to interpret this experiment

- The run demonstrates real model API connectivity, timing, token-based cost calculation and strict five-section Pydantic schema validation.
- `LLMServiceError` is a broad failure class covering provider HTTP status, network timeout, JSON parsing or Pydantic schema failure. **The terminal output alone does not establish the root cause** of the two failures.
- **Schema validity is not factual accuracy.** The outputs have not yet been manually scored for correct services, customer audiences, competitors, source grounding or SEO usefulness.
- The sample is small (three URLs and one attempt per model/site); Example.com is not a commercial business. The observed success rates and means should **not** be described as production reliability or definitive model accuracy.
- Successful-request averages exclude failed calls and the page-fetch step. Total user-perceived latency may be higher, especially if the service retries or fetches slower pages.
- The free-tier project shown in Google AI Studio had no billing set up; the benchmark's dollar figures do not imply charges to the account.

## Provisional engineering choice

**Primary for speed/cost:** `gemini-3.5-flash-lite`, which had the fastest average successful response in this run, but failed one of three test cases.
**Reliability-oriented fallback candidate:** `gemini-3.5-flash`, which validated all three outputs, but was materially slower and more expensive. The application has **not** implemented automatic fallback; this is a recommendation, not an existing feature.
**Lowest mean successful-call cost:** `gemini-3.1-flash-lite`, though it also failed one case.

Before a final model recommendation: diagnose both failure messages; manually assess the JSON snapshots in `benchmarks/sample_outputs/`; optionally repeat a small, controlled number of tests after any code fix, within the API quota. Do not assume a better factual answer just because a schema validated.

## Supporting files and reproducibility

- Raw local measurements: `benchmarks/results.csv` (generated during the user's live run; gitignored by default)
- Locally generated detailed responses: `benchmarks/sample_outputs/` (gitignored by default)
- Benchmark source: `scripts/benchmark_gemini.py`
- Three-provider documentation/pricing comparison: `MODEL_COMPARISON.md`

To reproduce (only if API quota allows; **this sends live requests**):

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmark_gemini --live
```

**Note for reviewers:** The numbers above are transcribed from the live terminal output. The underlying CSV should be kept locally for verification, and no unobserved accuracy or API billing figure is represented as measured.
