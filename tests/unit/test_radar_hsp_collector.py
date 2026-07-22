from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.radar_hsp import collect_hsp_file
from rainroute_data.collectors.raw_response import RawResponseCollector
from rainroute_data.schemas.manifest import CollectionStatus

KST = ZoneInfo("Asia/Seoul")


def test_collect_hsp_file_builds_expected_request(tmp_path) -> None:
    captured_url: httpx.URL | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = request.url

        return httpx.Response(
            status_code=200,
            content=b"hsp-binary",
            headers={"content-type": "text/plain"},
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

        manifest = collect_hsp_file(
            collector=collector,
            data_root=tmp_path,
            valid_time=datetime(
                2026,
                7,
                22,
                19,
                20,
                tzinfo=KST,
            ),
        )

    assert captured_url is not None
    assert captured_url.path.endswith("/rdr_cmp_file.php")
    assert captured_url.params["tm"] == "202607221920"
    assert captured_url.params["data"] == "bin"
    assert captured_url.params["cmp"] == "hsp"

    assert manifest.status == CollectionStatus.SUCCESS
    assert manifest.identity.product == "HSP"
    assert manifest.identity.variable == "rain_rate"
    assert manifest.artifact is not None
    assert manifest.artifact.content_type == "application/octet-stream"
    assert manifest.artifact.relative_path.startswith(
        "raw/radar_hsp/2026/07/22/"
    )
