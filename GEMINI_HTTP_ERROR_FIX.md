# Gemini upstream HTTP error handling fix (v1.2 hotfix)

This patch fixes a real observability/handling bug in the existing Dxora v1.2 release: a Gemini HTTP `429 RESOURCE_EXHAUSTED` was previously caught as a generic `LLMServiceError` and returned by FastAPI as `502 Bad Gateway`.

## Behavior after patch

- Gemini `429` -> API **429** with a sanitized description. If Google supplies a structured `RetryInfo.retryDelay` or `Retry-After` header, forward the numeric value as `Retry-After`.
- A daily-quota violation (`QuotaFailure.quotaId` indicating a daily quota) is **not** immediately retried.
- A transient `429` is retried **once only if** the upstream explicitly suggests a 1–3 second delay. An unknown/long retry delay is returned to the client without blocking or hammering Google's API.
- Gemini `500/502/503/504` -> up to 2 retries (1s then 2s); persistent provider failures -> API **503**.
- Gemini network timeout -> up to 2 retries; persistent timeout -> API **504**.
- Invalid Gemini response schema and unrelated fetch errors remain API **502**.
- No external paid services, no additional default model, no API key changes and no new runtime dependencies.

This addresses **error reporting and retry strategy**, not provider quota itself. The upstream `429` may still occur if the model is throttled, a per-project cap is exceeded, or the provider is temporarily busy. A `429` may occur even when the AI Studio aggregate usage chart does not show the daily request maximum being reached; the quota reason should not be invented.

## Local installation

From the project directory in Windows PowerShell:

```powershell
# Optional: preserve working files already present before overwriting them.
# This patch replaces only app/main.py, app/services/llm_service.py, README.md,
# and adds offline tests / documentation.
Expand-Archive -LiteralPath 'D:\Downloads\dxora-v1.2-gemini-502-429-fix.zip' -DestinationPath . -Force
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: **60 tests passing** if the folder has the established Dxora v1.2 baseline (49 tests). The additional **11 tests** simulate upstream HTTP errors offline and **do not contact Google or use API quota**.

Check `git diff --check` and review changes before committing. Do not push or deploy until you approve.

## Troubleshooting the actual 429

1. Check the active project/API key and `GEMINI_MODEL` in local `.env` and Render's Environment. Never paste the secret key into chats or commits.
2. Inspect model-specific rate-limit messages from Google AI Studio / provider logs, focusing on any `QuotaFailure` and `RetryInfo` details. Do not expose raw authenticated response bodies publicly.
3. If provider daily quota is genuinely exhausted, only quota reset/increase can allow further calls; retry loops cannot overcome it.
4. If provider capacity/throttling is temporary, honor `Retry-After` if supplied and avoid repeated clicks on Swagger `Execute`.

## Limitations

- Demo rate limits and rate-limit response codes are not a substitute for provider-level billing and usage caps.
- The server keeps no persistent central cooldown across multiple Render replicas.
- Model fallback is intentionally **not automatic**. If you ever want it, obtain consent about token costs, configure a permitted exact fallback model, and test different model outputs before enabling it.
- Google API key exposure is unrelated to this fix; rotate keys that may have been exposed.
