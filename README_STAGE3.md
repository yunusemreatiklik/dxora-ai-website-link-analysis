# Dxora – Stage 3: Real Gemini LLM analysis

**Source:** Dxora second assessment `AI-Powered Website Link Analysis API` (`chivoxai/practical-test/link-analysis.md`). The project is a working prototype, **not a finished submission**.

This package preserves the previously working stage-2 extractor and adds real Gemini API calls, five-section JSON validation, safe failure on missing keys/provider errors, and offline tests. It **does not** include verified competitor research, three-model cost/latency benchmarking, screenshots, GitHub publication, or a public demo. Those remain to do before submission.

## Installation in your Windows project folder

Run in `C:\Users\CASPER\dxora-link-analysis` (stop Uvicorn with Ctrl+C first):

```powershell
Copy-Item .\app\main.py .\app\main_stage2_backup.py -Force
# Extract the stage3 ZIP over this folder, preserving your .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The test suite uses **offline mock responses**: passing tests do not imply the Gemini API works with your credentials.

## Configure the Gemini API key privately

1. Open https://aistudio.google.com/apikey and create a Gemini API key. Verify any applicable costs and account restrictions before calling the API.
2. From the project folder: `Copy-Item .env.example .env`.
3. Open **.env locally** in VS Code, fill `GEMINI_API_KEY=...` with your real key and save it. **Do not paste the key into ChatGPT or commit it to GitHub.**
4. `GEMINI_MODEL=gemini-flash-latest` is an alias; it may resolve to a changing underlying model. For Dxora's pricing comparison, use a specific available model ID and cite the provider's current pricing.
5. Run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 4000 --reload
```

Browse http://127.0.0.1:4000/docs, select `POST /link-analysis`, then use:

```json
{"url":"https://www.python.org"}
```

A successful **real** analysis returns `success: true`, `status: "analysis_complete"`, `brand`, and `analysis` with exactly five sections: `competitor_analysis`, `target_search_queries`, `seo_improvements`, `top_services`, `target_audience`. The two lists `target_search_queries` and `top_services` each contain exactly five items. Items inferred from limited evidence are marked accordingly.

If no API key is configured, API returns HTTP **503** rather than fake success. If the LLM provider rejects, times out or returns invalid JSON, the API returns **502**. Review provider rate limits if HTTP 429 appears.

## Design notes / what remains

- Source website content is treated as **untrusted data**, not instructions.
- The fetcher rejects private/IP-literal internal addresses, follows redirects manually and limits page size. The DNS-precheck is not complete protection against DNS rebinding. **Before public deployment**, enforce outbound egress/network restrictions and use a transport that pins resolved public IPs across connection, or put it behind a trusted URL-fetch service.
- Competitors inferred by the LLM are marked `unverified_suggestion`; this demo does **not** independently research competitors. Reliable evidence may require an additional verified lookup workflow.
- Do not invent search volume, traffic metrics, competitor facts, or benchmark numbers.
- A static HTML fetch may not access JavaScript-rendered pages.
- Gemini tokens/latency and costs should be measured across multiple sites and compared against two other real models. See `MODEL_COMPARISON_TODO.md`.
- Add screenshot evidence, real tests, deployment URL including `/docs`, and GitHub repository link before sending to `hr@chivoxai.com`.
