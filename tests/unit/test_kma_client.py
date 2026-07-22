import httpx
import pytest

from rainroute_data.clients.kma import (
    KmaClient,
    KmaHttpStatusError,
)


def test_client_adds_key_but_returns_redacted_metadata() -> None:
    secret = "top-secret-key"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["authKey"] == secret
        assert request.url.params["tm"] == "202607221900"

        return httpx.Response(
            status_code=200,
            content=b"radar-data",
            headers={
                "content-type": "application/octet-stream",
            },
        )

    transport = httpx.MockTransport(handler)

    with KmaClient(
        api_key=secret,
        base_url="https://example.test",
        transport=transport,
    ) as client:
        response = client.get(
            "/radar",
            params={"tm": "202607221900"},
        )

    assert response.content == b"radar-data"
    assert secret not in response.request_url
    assert response.request_params["authKey"] == "***REDACTED***"
    assert response.status_code == 200


def test_http_error_does_not_leak_secret() -> None:
    secret = "top-secret-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=500,
            text=f"failed authKey={secret}",
        )

    transport = httpx.MockTransport(handler)

    with KmaClient(
        api_key=secret,
        base_url="https://example.test",
        transport=transport,
    ) as client:
        with pytest.raises(KmaHttpStatusError) as exc_info:
            client.get("/radar")

    assert secret not in str(exc_info.value)
    assert "***REDACTED***" in str(exc_info.value)


def test_endpoint_must_be_absolute_path() -> None:
    with KmaClient(
        api_key="secret",
        base_url="https://example.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200)
        ),
    ) as client:
        with pytest.raises(ValueError):
            client.get("radar")
