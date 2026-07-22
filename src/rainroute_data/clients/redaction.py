from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_KEYS = {
    "authkey",
    "api_key",
    "apikey",
    "authorization",
    "token",
    "access_token",
}

REDACTED = "***REDACTED***"

_SENSITIVE_FRAGMENT_PATTERN = re.compile(
    r"(?P<key>"
    r"authkey|api[_-]?key|apikey|authorization|access[_-]?token|token"
    r")=(?P<value>[^\s&]+)",
    flags=re.IGNORECASE,
)


def normalize_key(key: str) -> str:
    return key.lower().replace("-", "_")


def is_sensitive_key(key: str) -> bool:
    return normalize_key(key) in SENSITIVE_KEYS


def redact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy with credential-like values redacted."""
    return {
        key: REDACTED if is_sensitive_key(key) else value
        for key, value in values.items()
    }


def redact_url(url: str) -> str:
    """Redact sensitive query parameters from a URL."""
    parts = urlsplit(url)

    redacted_query = urlencode(
        [
            (key, REDACTED if is_sensitive_key(key) else value)
            for key, value in parse_qsl(
                parts.query,
                keep_blank_values=True,
            )
        ]
    )

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            redacted_query,
            parts.fragment,
        )
    )


def redact_text(
    text: str,
    *,
    secrets: tuple[str, ...] = (),
) -> str:
    """Remove known secrets and credential-style key-value fragments."""
    result = text

    for secret in secrets:
        if secret:
            result = result.replace(secret, REDACTED)

    return _SENSITIVE_FRAGMENT_PATTERN.sub(
        lambda match: f"{match.group('key')}={REDACTED}",
        result,
    )
