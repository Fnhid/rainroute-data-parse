from __future__ import annotations

from pathlib import Path
from typing import Literal

from rainroute_data.collectors.raw_response import RawResponseCollector
from rainroute_data.schemas.manifest import (
    CollectionManifest,
    DataIdentity,
    FileFormat,
)

CoordinateKind = Literal["lat", "lon"]

RADAR_LATLON_ENDPOINT = (
    "/api/typ01/cgi-bin/url/nph-rdr_latlon_api"
)


def radar_latlon_path(
    data_root: Path,
    *,
    product: str,
    coordinate: CoordinateKind,
) -> Path:
    filename = (
        "latitude.bin"
        if coordinate == "lat"
        else "longitude.bin"
    )

    return (
        data_root.expanduser().resolve()
        / "metadata"
        / "radar_grids"
        / product.upper()
        / filename
    )


def collect_radar_coordinate(
    *,
    collector: RawResponseCollector,
    data_root: Path,
    product: str,
    coordinate: CoordinateKind,
) -> CollectionManifest:
    product = product.upper()

    if product not in {"HSR", "HSP", "HCI", "PCP"}:
        raise ValueError(
            f"Unsupported radar coordinate product: {product}"
        )

    variable = (
        "latitude"
        if coordinate == "lat"
        else "longitude"
    )

    identity = DataIdentity(
        source="radar_grid_metadata",
        product=product,
        variable=variable,
        grid=f"{product}_native",
    )

    destination = radar_latlon_path(
        data_root,
        product=product,
        coordinate=coordinate,
    )

    return collector.collect(
        identity=identity,
        endpoint=RADAR_LATLON_ENDPOINT,
        params={
            "cmp": product,
            "latlon": coordinate,
            "disp": "B",
        },
        destination=destination,
        file_format=FileFormat.BINARY,
        content_type_override="application/octet-stream",
    )


def collect_radar_latlon_pair(
    *,
    collector: RawResponseCollector,
    data_root: Path,
    product: str,
) -> tuple[CollectionManifest, CollectionManifest]:
    latitude_manifest = collect_radar_coordinate(
        collector=collector,
        data_root=data_root,
        product=product,
        coordinate="lat",
    )

    longitude_manifest = collect_radar_coordinate(
        collector=collector,
        data_root=data_root,
        product=product,
        coordinate="lon",
    )

    return latitude_manifest, longitude_manifest
