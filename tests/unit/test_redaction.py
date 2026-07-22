from rainroute_data.clients.redaction import (
    REDACTED,
    redact_mapping,
    redact_text,
    redact_url,
)


def test_redact_mapping() -> None:
    result = redact_mapping(
        {
            "authKey": "secret",
            "tm": "202607221900",
        }
    )

    assert result["authKey"] == REDACTED
    assert result["tm"] == "202607221900"


def test_redact_url() -> None:
    url = (
        "https://example.test/data"
        "?tm=202607221900&authKey=secret"
    )

    redacted = redact_url(url)

    assert "secret" not in redacted
    assert "authKey=%2A%2A%2AREDACTED%2A%2A%2A" in redacted
    assert "tm=202607221900" in redacted


def test_redact_text_known_secret() -> None:
    result = redact_text(
        "request failed using key abc123",
        secrets=("abc123",),
    )

    assert "abc123" not in result
    assert REDACTED in result


def test_redact_text_query_fragment() -> None:
    result = redact_text(
        "URL failed: authKey=abc123&tm=20260722"
    )

    assert "abc123" not in result
    assert "authKey=***REDACTED***" in result


def test_redact_text_is_case_insensitive() -> None:
    samples = (
        "authKey=secret",
        "AUTHKEY=secret",
        "ApiKey=secret",
        "api_key=secret",
        "access-token=secret",
    )

    for sample in samples:
        result = redact_text(sample)

        assert "secret" not in result
        assert REDACTED in result
