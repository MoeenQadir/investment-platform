"""Tests for app.services.edgar.sec_client."""
from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from app.services.edgar.sec_client import SecClient, SecClientError


def test_missing_user_agent_raises(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(SecClientError):
        SecClient()


def test_empty_user_agent_raises(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "   ")
    with pytest.raises(SecClientError):
        SecClient()


@pytest.mark.asyncio
async def test_user_agent_header_sent(monkeypatch):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["ua"] = request.headers.get("user-agent")
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setenv("SEC_USER_AGENT", "TestCo test@example.com")
    transport = httpx.MockTransport(handler)
    async with SecClient(transport=transport, rate_limit=50) as client:
        data = await client.get_json("/files/company_tickers.json", base="www")

    assert data == {"ok": True}
    assert captured["ua"] == "TestCo test@example.com"
    assert captured["url"].startswith("https://www.sec.gov/")


@pytest.mark.asyncio
async def test_rate_limit_throttles_requests(monkeypatch):
    """At rate_limit=5 req/s, 5 sequential requests should take >= 4 * 0.2s ≈ 0.8s."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"i": 1})

    monkeypatch.setenv("SEC_USER_AGENT", "TestCo t@example.com")
    transport = httpx.MockTransport(handler)
    async with SecClient(transport=transport, rate_limit=5) as client:
        start = time.monotonic()
        for _ in range(5):
            await client.get_json("/x", base="www")
        elapsed = time.monotonic() - start

    # 5 requests at min-interval 0.2s => ~0.8s minimum between request starts
    assert elapsed >= 0.7, f"expected throttling, got {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds(monkeypatch):
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(429, headers={"Retry-After": "0"}, text="slow down")
        return httpx.Response(200, json={"done": True})

    monkeypatch.setenv("SEC_USER_AGENT", "TestCo t@example.com")
    transport = httpx.MockTransport(handler)
    async with SecClient(transport=transport, rate_limit=50) as client:
        result = await client.get_json("/x", base="www")
    assert result == {"done": True}
    assert attempts["n"] == 3


@pytest.mark.asyncio
async def test_concurrent_requests_bounded_by_semaphore(monkeypatch):
    """Semaphore should cap concurrent in-flight calls at rate_limit."""
    in_flight = {"current": 0, "peak": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        in_flight["current"] += 1
        in_flight["peak"] = max(in_flight["peak"], in_flight["current"])
        await asyncio.sleep(0.05)
        in_flight["current"] -= 1
        return httpx.Response(200, json={})

    monkeypatch.setenv("SEC_USER_AGENT", "TestCo t@example.com")
    transport = httpx.MockTransport(handler)
    async with SecClient(transport=transport, rate_limit=3) as client:
        await asyncio.gather(*(client.get_json(f"/p{i}", base="www") for i in range(10)))

    assert in_flight["peak"] <= 3
