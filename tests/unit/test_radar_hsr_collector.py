from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.radar_hsr import (
    collect_hsr_grid,
)
from rainroute_data.collectors.raw_response import (
    RawResponseCollector,
)
from rainroute_data.schemas.manifest import CollectionStatus

KST = ZoneInfo("Asia/Seoul")


def test_collect_hsr_grid_builds_expected_request(
    tmp_path,
) -> None:
    captured_url: httpx.URL | None = None

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal captured_url
        captured_url = request.url

        return httpx.Response(
            status_code=200,
            content=b"\x01\x00\x01\x00\x64\x00",
            headers={
                "content-type": "application/octet-stream",
            },
        )

    with KmaClient(
        api_key="secret",
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        raw_collector = RawResponseCollector(
            client=client,
            data_root=tmp_path,
        )

        manifest = collect_hsr_grid(
            collector=raw_collector,
            data_root=tmp_path,
            valid_time=datetime(
                2026,
                7,
                22,
                19,
                30,
                tzinfo=KST,
            ),
        )

    assert captured_url is not None
    assert captured_url.path.endswith(
        "/nph-rdr_cmp1_api"
    )
    assert captured_url.params["tm"] == "202607221930"
    assert captured_url.params["cmp"] == "HSR"
    assert captured_url.params["qcd"] == "MSK"
    assert captured_url.params["obs"] == "ECHO"
    assert captured_url.params["map"] == "HB"
    assert captured_url.params["disp"] == "B"

    assert manifest.status == CollectionStatus.SUCCESS
    assert manifest.identity.product == "HSR"
    assert manifest.identity.grid == "HB_500m"
    assert manifest.artifact is not None
    assert manifest.artifact.relative_path.startswith(
        "raw/radar_hsr/2026/07/22/"
    )
