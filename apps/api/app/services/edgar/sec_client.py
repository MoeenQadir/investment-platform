"""Async SEC EDGAR HTTP client with rate limiting and retry."""
from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import httpx


class SecClientError(Exception):
    """Raised for unrecoverable SEC client errors."""


DEFAULT_BASE_URL = "https://www.sec.gov"
DEFAULT_DATA_URL = "https://data.sec.gov"
DEFAULT_RATE_LIMIT = 10  # requests per second
MAX_RETRIES = 5
INITIAL_BACKOFF_SEC = 1.0
RETRY_STATUSES = {429, 503}


class SecClient:
    """Async EDGAR client. Enforces SEC fair-access policy: declared UA + 10 req/s.

    Usage:
        async with SecClient() as client:
            data = await client.get_json("/files/company_tickers.json", base="www")
    """

    def __init__(
        self,
        user_agent: Optional[str] = None,
        rate_limit: Optional[int] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = 30.0,
    ) -> None:
        ua = user_agent if user_agent is not None else os.getenv("SEC_USER_AGENT", "")
        if not ua or not ua.strip():
            raise SecClientError(
                "SEC_USER_AGENT env var is required (format: 'Sample Co contact@example.com')"
            )
        self.user_agent = ua.strip()

        if rate_limit is None:
            env_rate = os.getenv("EDGAR_RATE_LIMIT")
            rate_limit = int(env_rate) if env_rate else DEFAULT_RATE_LIMIT
        if rate_limit <= 0:
            raise SecClientError("rate_limit must be > 0")
        self.rate_limit = rate_limit
        self._semaphore = asyncio.Semaphore(rate_limit)
        self._min_interval = 1.0 / rate_limit
        self._last_request_at = 0.0
        self._interval_lock = asyncio.Lock()

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
        }
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
        )

    async def __aenter__(self) -> "SecClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _resolve_url(self, path: str, base: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if base == "data":
            root = DEFAULT_DATA_URL
        else:
            root = DEFAULT_BASE_URL
        if not path.startswith("/"):
            path = "/" + path
        return root + path

    async def _throttle(self) -> None:
        async with self._interval_lock:
            now = asyncio.get_event_loop().time()
            delta = now - self._last_request_at
            wait = self._min_interval - delta
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_at = asyncio.get_event_loop().time()

    async def request(
        self,
        method: str,
        path: str,
        base: str = "www",
        **kwargs: Any,
    ) -> httpx.Response:
        url = self._resolve_url(path, base)
        backoff = INITIAL_BACKOFF_SEC
        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            async with self._semaphore:
                await self._throttle()
                try:
                    response = await self._client.request(method, url, **kwargs)
                except httpx.HTTPError as exc:
                    last_exc = exc
                    if attempt == MAX_RETRIES - 1:
                        raise SecClientError(f"HTTP error after {MAX_RETRIES} retries: {exc}") from exc
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue

            if response.status_code in RETRY_STATUSES:
                if attempt == MAX_RETRIES - 1:
                    raise SecClientError(
                        f"SEC returned {response.status_code} after {MAX_RETRIES} retries for {url}"
                    )
                retry_after = response.headers.get("Retry-After")
                sleep_for = float(retry_after) if retry_after and retry_after.isdigit() else backoff
                await asyncio.sleep(sleep_for)
                backoff *= 2
                continue

            if response.status_code >= 400:
                raise SecClientError(
                    f"SEC HTTP {response.status_code} for {url}: {response.text[:200]}"
                )
            return response

        if last_exc is not None:
            raise SecClientError(f"Exhausted retries: {last_exc}") from last_exc
        raise SecClientError(f"Exhausted retries for {url}")

    async def get_json(self, path: str, base: str = "www", **kwargs: Any) -> Any:
        response = await self.request("GET", path, base=base, **kwargs)
        return response.json()

    async def get_text(self, path: str, base: str = "www", **kwargs: Any) -> str:
        response = await self.request("GET", path, base=base, **kwargs)
        return response.text

    async def get_bytes(self, path: str, base: str = "www", **kwargs: Any) -> bytes:
        response = await self.request("GET", path, base=base, **kwargs)
        return response.content


_SHARED_CLIENT: Optional[SecClient] = None
_SHARED_CLIENT_LOCK = asyncio.Lock()


async def get_shared_client() -> SecClient:
    """Return the process-wide SecClient singleton, constructing on first call.

    Use this in async code paths that don't already have a SecClient injected.
    Centralizing the client guarantees SEC's 10 req/s fair-access policy is
    enforced across all callers in the same process — each new SecClient
    would otherwise get its own semaphore and could exceed the cap together.
    """
    global _SHARED_CLIENT
    if _SHARED_CLIENT is not None:
        return _SHARED_CLIENT
    async with _SHARED_CLIENT_LOCK:
        if _SHARED_CLIENT is None:
            _SHARED_CLIENT = SecClient()
    return _SHARED_CLIENT


async def reset_shared_client() -> None:
    """Close and clear the singleton. Test/teardown only."""
    global _SHARED_CLIENT
    async with _SHARED_CLIENT_LOCK:
        if _SHARED_CLIENT is not None:
            await _SHARED_CLIENT.aclose()
            _SHARED_CLIENT = None
