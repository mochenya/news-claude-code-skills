from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Final

import httpx

DEFAULT_BASE_URL: Final[str] = "https://nitter.net"
DEFAULT_TIMEOUT: Final[float] = 20.0
DEFAULT_MAX_RETRIES: Final[int] = 2
DEFAULT_RETRY_DELAY_SECONDS: Final[float] = 0.5
RETRYABLE_STATUS_CODES: Final[set[int]] = {429, 500, 502, 503, 504}
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.RemoteProtocolError,
    httpx.PoolTimeout,
)
DEFAULT_HEADERS: Final[dict[str, str]] = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}


@dataclass(slots=True)
class RSSResponse:
    username: str
    rss_url: str
    final_url: str
    status_code: int
    content_type: str
    xml_text: str


class RSSClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self.retry_delay_seconds = max(0.0, float(retry_delay_seconds))

    def build_rss_url(self, username: str) -> str:
        clean = username.strip().lstrip("@")
        return f"{self.base_url}/{clean}/rss"

    def create_async_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout, headers=DEFAULT_HEADERS, follow_redirects=True)

    def _build_response(self, username: str, rss_url: str, response: httpx.Response) -> RSSResponse:
        content_type = response.headers.get("content-type", "")
        if "xml" not in content_type and "rss" not in content_type and "text" not in content_type:
            raise ValueError(f"Unexpected content-type: {content_type}")
        text = response.text.strip()
        if "<rss" not in text and "<feed" not in text:
            raise ValueError("Response is not RSS/Atom XML")
        return RSSResponse(
            username=username.strip().lstrip("@"),
            rss_url=rss_url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=content_type,
            xml_text=text,
        )

    def _request_with_retry(self, client: httpx.Client, rss_url: str) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = client.get(rss_url)
                if response.status_code >= 400:
                    if response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                        time.sleep(self.retry_delay_seconds)
                        continue
                    response.raise_for_status()
                return response
            except RETRYABLE_EXCEPTIONS:
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.retry_delay_seconds)

        raise RuntimeError("unreachable")

    async def _request_with_retry_async(self, client: httpx.AsyncClient, rss_url: str) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.get(rss_url)
                if response.status_code >= 400:
                    if response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay_seconds)
                        continue
                    response.raise_for_status()
                return response
            except RETRYABLE_EXCEPTIONS:
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(self.retry_delay_seconds)

        raise RuntimeError("unreachable")

    def fetch_user_rss(self, username: str) -> RSSResponse:
        rss_url = self.build_rss_url(username)
        with httpx.Client(timeout=self.timeout, headers=DEFAULT_HEADERS, follow_redirects=True) as client:
            response = self._request_with_retry(client, rss_url)
            return self._build_response(username, rss_url, response)

    async def fetch_user_rss_async(self, username: str, client: httpx.AsyncClient | None = None) -> RSSResponse:
        rss_url = self.build_rss_url(username)

        if client is not None:
            response = await self._request_with_retry_async(client, rss_url)
            return self._build_response(username, rss_url, response)

        async with self.create_async_client() as async_client:
            response = await self._request_with_retry_async(async_client, rss_url)
            return self._build_response(username, rss_url, response)
