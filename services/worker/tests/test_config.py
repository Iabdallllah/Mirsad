"""Worker config tests: defaults must match plan.md §12.3."""

from __future__ import annotations

import pytest

from mirsad_worker.config import WorkerSettings


def test_defaults_match_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "SCAN_MAX_DURATION_MIN",
        "SCAN_MAX_TOKENS",
        "SCAN_MAX_LLM_CALLS",
        "SCAN_MAX_REQUESTS_SAFE",
        "SCAN_MAX_REQUESTS_DEEP",
        "WORKER_CONCURRENCY",
        "WORKER_LEASE_TIMEOUT_SEC",
    ):
        monkeypatch.delenv(var, raising=False)
    settings = WorkerSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.scan_max_duration_min == 15
    assert settings.scan_max_tokens == 100_000
    assert settings.scan_max_llm_calls == 25
    assert settings.scan_max_requests_safe == 300
    assert settings.scan_max_requests_deep == 600
    assert settings.worker_concurrency == 2
    assert settings.worker_lease_timeout_sec == 120


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCAN_MAX_REQUESTS_SAFE", "200")
    settings = WorkerSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.scan_max_requests_safe == 200
