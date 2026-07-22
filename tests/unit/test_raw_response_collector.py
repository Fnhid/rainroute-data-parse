import json
from datetime import UTC, datetime

import httpx
import pytest

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.raw_response import RawResponseCollector
from rainroute_data.schemas.manifest import (
    CollectionStatus,
    DataIdentity,
    FileFormat,
)
from rainroute_data.storage.layout import manifest_path_for


def test_collects_raw_response_and_manifest(tmp_path) -> None:
    secret = "secret-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            content=b"hsp-binary",
            headers={
                "content-type": "application/octet-stream",
            },
        )

    destination = (
        tmp_path
        / "raw"
        / "radar_hsp"
        / "2026"
        / "07"
        / "22"
        / "sample.bin"
    )

    identity = DataIdentity(
        source="radar_hsp",
        product="HSP",
        valid_time=datetime(
            2026,
            7,
            22,
            10,
            0,
            tzinfo=UTC,
        ),
        variable="rain_rate",
        grid="HB_500m",
    )

    with KmaClient(
        api_key=secret,
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        collector = RawResponseCollector(
            client=client,
            data_root=tmp_path,
        )

        manifest = collector.collect(
            identity=identity,
            endpoint="/radar",
            params={
                "tm": "202607221900",
                "cmp": "HSP",
            },
            destination=destination,
            file_format=FileFormat.BINARY,
        )

    assert manifest.status == CollectionStatus.SUCCESS
    assert destination.read_bytes() == b"hsp-binary"

    stored_manifest = json.loads(
        manifest_path_for(destination).read_text(
            encoding="utf-8"
        )
    )

    serialized = json.dumps(stored_manifest)

    assert secret not in serialized
    assert stored_manifest["request"]["params"]["authKey"] == (
        "***REDACTED***"
    )
    assert stored_manifest["artifact"]["size_bytes"] == 10


def test_duplicate_does_not_rewrite_manifest(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            content=b"same-data",
        )

    destination = tmp_path / "raw" / "sample.bin"

    identity = DataIdentity(
        source="radar_hsp",
        product="HSP",
        valid_time=datetime.now(UTC),
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

        first = collector.collect(
            identity=identity,
            endpoint="/radar",
            params={},
            destination=destination,
            file_format=FileFormat.BINARY,
        )

        manifest_path = manifest_path_for(destination)
        original_manifest = manifest_path.read_bytes()

        second = collector.collect(
            identity=identity,
            endpoint="/radar",
            params={},
            destination=destination,
            file_format=FileFormat.BINARY,
        )

    assert first.status == CollectionStatus.SUCCESS
    assert second.status == CollectionStatus.DUPLICATE
    assert manifest_path.read_bytes() == original_manifest


def test_destination_must_be_inside_data_root(tmp_path) -> None:
    with KmaClient(
        api_key="secret",
        base_url="https://example.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=b"data",
            )
        ),
    ) as client:
        collector = RawResponseCollector(
            client=client,
            data_root=tmp_path / "data",
        )

        with pytest.raises(ValueError):
            collector.collect(
                identity=DataIdentity(
                    source="radar_hsp",
                    product="HSP",
                    valid_time=datetime.now(UTC),
                ),
                endpoint="/radar",
                params={},
                destination=tmp_path / "outside.bin",
                file_format=FileFormat.BINARY,
            )
