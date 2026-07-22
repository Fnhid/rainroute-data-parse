from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.aws_minute import (
    collect_aws_minute,
)
from rainroute_data.collectors.aws_stations import (
    collect_aws_stations,
)
from rainroute_data.collectors.raw_response import (
    RawResponseCollector,
)

KST = ZoneInfo("Asia/Seoul")


def test_collect_aws_minute(tmp_path) -> None:
    captured_url: httpx.URL | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = request.url

        return httpx.Response(
            status_code=200,
            content=b"# help\n202607221910,108,...\n",
        )

    with KmaClient(
        api_key="secret",
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        collector = RawResponseCollector(
            client=client,
            data_root=tmp_path,
        )

        manifest = collect_aws_minute(
            collector=collector,
            data_root=tmp_path,
            start_time=datetime(
                2026, 7, 22, 19, 5, tzinfo=KST
            ),
            end_time=datetime(
                2026, 7, 22, 19, 10, tzinfo=KST
            ),
        )

    assert captured_url is not None
    assert captured_url.params["tm1"] == "202607221905"
    assert captured_url.params["tm2"] == "202607221910"
    assert captured_url.params["stn"] == "0"
    assert captured_url.params["disp"] == "1"
    assert captured_url.params["help"] == "1"

    assert manifest.artifact is not None
    assert manifest.artifact.relative_path.startswith(
        "raw/aws_minute/2026/07/22/"
    )


def test_rejects_long_all_station_request(tmp_path) -> None:
    with KmaClient(
        api_key="secret",
        base_url="https://example.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200)
        ),
    ) as client:
        collector = RawResponseCollector(
            client=client,
            data_root=tmp_path,
        )

        with pytest.raises(
            ValueError,
            match="must not exceed 10 minutes",
        ):
            collect_aws_minute(
                collector=collector,
                data_root=tmp_path,
                start_time=datetime(
                    2026, 7, 22, 18, 50, tzinfo=KST
                ),
                end_time=datetime(
                    2026, 7, 22, 19, 10, tzinfo=KST
                ),
            )


def test_collect_aws_stations(tmp_path) -> None:
    captured_url: httpx.URL | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = request.url

        return httpx.Response(
            status_code=200,
            content=b"# station metadata\n",
        )

    with KmaClient(
        api_key="secret",
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        collector = RawResponseCollector(
            client=client,
            data_root=tmp_path,
        )

        manifest = collect_aws_stations(
            collector=collector,
            data_root=tmp_path,
        )

    assert captured_url is not None
    assert captured_url.params["inf"] == "AWS"
    assert captured_url.params["stn"] == "0"
    assert captured_url.params["help"] == "1"

    assert manifest.artifact is not None
    assert manifest.artifact.relative_path == (
        "metadata/aws/stations.txt"
    )
