from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from rainroute_data.collectors.raw_response import RawResponseCollector
from rainroute_data.schemas.manifest import (
    CollectionManifest,
    DataIdentity,
    FileFormat,
)

AWS_STATION_ENDPOINT = "/api/typ01/url/stn_inf.php"


def aws_station_path(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "metadata"
        / "aws"
        / "stations.txt"
    )


def collect_aws_stations(
    *,
    collector: RawResponseCollector,
    data_root: Path,
) -> CollectionManifest:
    identity = DataIdentity(
        source="aws_station_metadata",
        product="AWS",
        valid_time=datetime.now(UTC),
        variable="station_catalog",
        grid="station",
    )

    return collector.collect(
        identity=identity,
        endpoint=AWS_STATION_ENDPOINT,
        params={
            "inf": "AWS",
            "stn": 0,
            "help": 1,
        },
        destination=aws_station_path(data_root),
        file_format=FileFormat.TEXT,
        content_type_override="text/plain; charset=utf-8",
    )
