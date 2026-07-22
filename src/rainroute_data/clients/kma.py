from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from rainroute_data.clients.redaction import (
    redact_mapping,
    redact_text,
    redact_url,
)


class KmaClientError(RuntimeError):
    """Base error for KMA API requests."""


class KmaTransportError(KmaClientError):
    """Network or protocol-level request failure."""


class KmaHttpStatusError(KmaClientError):
    """KMA API returned a non-success HTTP status."""

    def __init__(
        self,
        *,
        status_code: int,
        body_preview: str,
    ) -> None:
        self.status_code = status_code
        self.body_preview = body_preview

        super().__init__(
            f"KMA API returned HTTP {status_code}: {body_preview}"
        )


@dataclass(frozen=True)
class KmaResponse:
    content: bytes
    status_code: int
    content_type: str | None
    elapsed_ms: int
    request_url: str
    request_params: dict[str, Any]


class KmaClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://apihub.kma.go.kr",
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key must not be empty")

        self._api_key = api_key
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
            transport=transport,
            headers={
                "User-Agent": "rainroute-data-pipeline/0.1",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> KmaClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> KmaResponse:
        if not endpoint.startswith("/"):
            raise ValueError("endpoint must start with '/'")

        request_params = dict(params or {})
        request_params["authKey"] = self._api_key

        started_at = time.monotonic()

        try:
            response = self._client.get(
                endpoint,
                params=request_params,
            )
        except httpx.HTTPError as exc:
            message = redact_text(
                str(exc),
                secrets=(self._api_key,),
            )
            raise KmaTransportError(message) from exc

        elapsed_ms = round(
            (time.monotonic() - started_at) * 1000
        )

        redacted_url = redact_url(str(response.request.url))
        redacted_params = redact_mapping(request_params)

        if not response.is_success:
            body_preview = redact_text(
                response.text[:500],
                secrets=(self._api_key,),
            )

            raise KmaHttpStatusError(
                status_code=response.status_code,
                body_preview=body_preview,
            )

        return KmaResponse(
            content=response.content,
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            elapsed_ms=elapsed_ms,
            request_url=redacted_url,
            request_params=redacted_params,
        )
