# Dxora Link Analysis — Step 2: Website content extraction

This stage adds an HTTP(S) site fetcher, manual redirect validation, response size and content-type limits, DNS/IP public-address checks, and BeautifulSoup text extraction.

**Important:** The required LLM analysis, five analytical sections, provider/model comparison, and public demo deployment are NOT implemented yet. The API intentionally returns `success=false` until they are.

## Windows setup

From `C:\Users\CASPER\dxora-link-analysis` after copying package contents into this folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 4000 --reload
```

Open `http://127.0.0.1:4000/docs` and submit `{"url":"https://example.com"}` to `POST /link-analysis`.

Expected: `status="extraction_complete"`, HTML page title/text preview, and `success=false` (LLM not done).

## Security note

Public-only URL validation, per-hop redirect checks, standard-port restrictions and bounded responses mitigate common SSRF routes. DNS-rebinding between preflight and socket connection remains a residual risk; production hosting should enforce outbound network egress restrictions and/or a DNS-pinning transport. Do not deploy this intermediate stage publicly as if fully production-hardened.
