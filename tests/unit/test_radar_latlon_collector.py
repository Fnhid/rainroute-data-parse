import struct

import httpx

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.radar_latlon import (
    collect_radar_latlon_pair,
    radar_latlon_path,
)
from rainroute_data.collectors.raw_response import (
    RawResponseCollector,
)
from rainroute_data.schemas.manifest import CollectionStatus


def make_payload(value: float) -> bytes:
    # Coordinate endpoint header order is (ny, nx).
    return struct.pack("<hhf", 1, 1, value)


def test_collect_radar_latlon_pair(tmp_path) -> None:
    requested_coordinates: list[str] = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        coordinate = request.url.params["latlon"]
        requested_coordinates.append(coordinate)

        value = 37.5 if coordinate == "lat" else 127.0

        return httpx.Response(
            status_code=200,
            content=make_payload(value),
            headers={"content-type": "text/plain"},
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

        latitude_manifest, longitude_manifest = (
            collect_radar_latlon_pair(
                collector=raw_collector,
                data_root=tmp_path,
                product="HSR",
            )
        )

    assert requested_coordinates == ["lat", "lon"]

    assert (
        latitude_manifest.status
        == CollectionStatus.SUCCESS
    )
    assert (
        longitude_manifest.status
        == CollectionStatus.SUCCESS
    )

    assert (
        latitude_manifest.artifact is not None
    )
    assert (
        longitude_manifest.artifact is not None
    )

    assert (
        latitude_manifest.artifact.content_type
        == "application/octet-stream"
    )

    assert radar_latlon_path(
        tmp_path,
        product="HSR",
        coordinate="lat",
    ).exists()

    assert radar_latlon_path(
        tmp_path,
        product="HSR",
        coordinate="lon",
    ).exists()
