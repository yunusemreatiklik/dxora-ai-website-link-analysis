"""Reproducible LIVE Gemini benchmark. Requires --live (may consume credits).

Runs the *same* three public sites through three model IDs sequentially.
Offline comparisons of other providers are documented separately in README.
Never writes API keys or extracted private information to output files.
"""
import argparse
import asyncio
import csv
import json
import hashlib
from datetime import datetime, timezone
import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from app.services.website_extractor import fetch_website
from app.services.llm_service import analyze_with_gemini

# USD per million tokens, standard paid tier, as published by Google in Nov 2026.
PRICES = {
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.5-flash": (1.50, 9.00),
}
SITES = [
    "https://www.atlassian.com/software/jira",
    "https://www.python.org",
    "https://example.com",
]


def estimate_cost(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    if model not in PRICES or input_tokens is None or output_tokens is None:
        return None
    p_in, p_out = PRICES[model]
    return (input_tokens * p_in + output_tokens * p_out) / 1_000_000


async def run(models: list[str], sites: list[str], output_file: Path):
    rows = []
    for site in sites:
        try:
            page = await fetch_website(site)
        except Exception as exc:
            print(f"FETCH FAILED {site}: {type(exc).__name__}")
            for model in models:
                rows.append({"timestamp_utc": datetime.now(timezone.utc).isoformat(), "url": site,
                    "model": model, "success": False, "error": "website_fetch_error"})
            continue
        for model in models:
            os.environ["GEMINI_MODEL"] = model
            started = perf_counter()
            row = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "url": site, "model": model, "source_characters": page.characters_extracted}
            try:
                result = await analyze_with_gemini(page)
                row.update({
                    "success": True,
                    "http_llm_seconds": result.response_seconds,
                    "end_to_end_seconds_excluding_fetch": round(perf_counter()-started, 3),
                    "input_tokens": result.usage.get("input_tokens"),
                    "output_tokens": result.usage.get("output_tokens"),
                    "total_tokens": result.usage.get("total_tokens"),
                    "estimated_paid_usd": estimate_cost(
                        model, result.usage.get("input_tokens"), result.usage.get("output_tokens")),
                    "competitors_count": len(result.result.analysis.competitor_analysis.competitors),
                    "queries_count": len(result.result.analysis.target_search_queries),
                    "services_count": len(result.result.analysis.top_services),
                    "json_schema_valid": True,
                    "error": "",
                })
                output_file.parent.mkdir(parents=True, exist_ok=True)
                snapshot_name = hashlib.sha256(f"{site}::{model}".encode()).hexdigest()[:12]
                snapshots = output_file.parent / "sample_outputs"
                snapshots.mkdir(exist_ok=True)
                with (snapshots / f"{model}-{snapshot_name}.json").open("w", encoding="utf-8") as fh:
                    json.dump({"url": site, "model": model,
                               "analysis": result.result.model_dump()}, fh, ensure_ascii=False, indent=2)
                print(f"OK: {site} / {model}: {row['http_llm_seconds']} s; ${row['estimated_paid_usd']}")
            except Exception as exc:
                row.update({"success": False, "json_schema_valid": False,
                    "end_to_end_seconds_excluding_fetch": round(perf_counter()-started, 3),
                    "error": type(exc).__name__})
                print(f"FAILED: {site} / {model}: {type(exc).__name__}")
            rows.append(row)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fields = ["timestamp_utc", "url", "model", "source_characters", "success",
              "http_llm_seconds", "end_to_end_seconds_excluding_fetch", "input_tokens",
              "output_tokens", "total_tokens", "estimated_paid_usd", "competitors_count",
              "queries_count", "services_count", "json_schema_valid", "error"]
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved reproducible measured results to {output_file}")
    print("Accuracy requires MANUAL evaluation of factual grounding; do not treat schema success as factual accuracy.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live, paid-usage-possible Gemini model benchmark")
    parser.add_argument("--live", action="store_true", help="Actually perform Gemini requests")
    parser.add_argument("--models", nargs="+", default=list(PRICES))
    parser.add_argument("--sites", nargs="+", default=SITES)
    parser.add_argument("--output", default="benchmarks/results.csv")
    args = parser.parse_args()
    if not args.live:
        parser.print_help()
        print("\nNothing sent. Add --live to run nine model/site combinations (may incur charges).")
        raise SystemExit(0)
    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY missing in local .env")
    asyncio.run(run(args.models, args.sites, Path(args.output)))
