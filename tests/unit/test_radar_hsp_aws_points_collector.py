from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.radar_hsp_aws_points import (
    collect_hsp_aws_points,
    hsp_aws_points_path,
)
from rainroute_data.collectors.raw_response import (
    RawResponseCollector,
)

KST = ZoneInfo("Asia/Seoul")


def test_hsp_aws_points_path(tmp_path) -> None:
    path = hsp_aws_points_path(
        tmp_path,
        valid_time=datetime(
            2026,
            7,
            22,
            19,
            10,
            tzinfo=KST,
        ),
        quality_code="EXT",
    )

    assert path == (
        tmp_path
        / "raw"
        / "radar_hsp_aws_points"
        / "2026"
        / "07"
        / "22"
        / "HSP_AWS_20260722T191000+0900_EXT.txt"
    )


def test_collect_hsp_aws_points(tmp_path) -> None:
    captured_url: httpx.URL | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = request.url

        return httpx.Response(
            status_code=200,
            content=(
                b"#START7777\n"
                b"202607221910,95,HSP,EXT,6.710,98.0,station,,=\n"
            ),
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

        manifest = collect_hsp_aws_points(
            collector=collector,
            data_root=tmp_path,
            valid_time=datetime(
                2026,
                7,
                22,
                19,
                10,
                tzinfo=KST,
            ),
            quality_code="EXT",
        )

    assert captured_url is not None
    assert captured_url.path.endswith(
        "/nph-rdr_cmp_aws_all_pt_data"
    )
    assert captured_url.params["tm"] == "202607221910"
    assert captured_url.params["qcd"] == "EXT"
    assert captured_url.params["cmp"] == "HSP"
    assert captured_url.params["help"] == "1"

    assert manifest.artifact is not None
    assert manifest.artifact.relative_path.endswith(
        "HSP_AWS_20260722T191000+0900_EXT.txt"
    )


def test_rejects_invalid_quality_code(tmp_path) -> None:
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
            match="quality_code",
        ):
            collect_hsp_aws_points(
                collector=collector,
                data_root=tmp_path,
                valid_time=datetime(
                    2026,
                    7,
                    22,
                    19,
                    10,
                    tzinfo=KST,
                ),
                quality_code="INVALID",
            )
