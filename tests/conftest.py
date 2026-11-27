"""Keep API tests independent of the process-wide demo limiter.

The app's live limiter remains unchanged. Individual limiter behaviour is
covered by dedicated DemoLimiter tests.
"""
import pytest

from app.limits import DemoLimiter


@pytest.fixture(autouse=True)
def isolated_demo_limiter(monkeypatch):
    # Guarantee existing regression tests never call a real backup provider,
    # even when the developer's local .env enables it.
    monkeypatch.setenv("FALLBACK_PROVIDER", "none")
    monkeypatch.setenv("GEMINI_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "60")
    monkeypatch.setattr("app.main.limiter", DemoLimiter(per_minute=100, per_day=100, parallel=4))
