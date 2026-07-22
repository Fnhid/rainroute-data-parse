from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from rainroute_data.collectors.raw_response import RawResponseCollector
from rainroute_data.schemas.manifest import (
    CollectionManifest,
    DataIdentity,
    FileFormat,
)
from rainroute_data.storage.layout import raw_artifact_path

KST = ZoneInfo("Asia/Seoul")

HSR_GRID_ENDPOINT = (
    "/api/typ01/cgi-bin/url/nph-rdr_cmp1_api"
)


def require_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("valid_time must be timezone-aware")

    return value.astimezone(KST)


def collect_hsr_grid(
    *,
    collector: RawResponseCollector,
    data_root: Path,
    valid_time: datetime,
    qcd: str = "MSK",
    map_code: str = "HB",
) -> CollectionManifest:
    valid_time_kst = require_kst(valid_time)

    identity = DataIdentity(
        source="radar_hsr",
        product="HSR",
        valid_time=valid_time_kst,
        variable="reflectivity",
        grid=f"{map_code}_500m",
    )

    destination = raw_artifact_path(
        data_root,
        identity,
        suffix="bin",
    )

    return collector.collect(
        identity=identity,
        endpoint=HSR_GRID_ENDPOINT,
        params={
            "tm": valid_time_kst.strftime("%Y%m%d%H%M"),
            "cmp": "HSR",
            "qcd": qcd,
            "obs": "ECHO",
            "map": map_code,
            "disp": "B",
        },
        destination=destination,
        file_format=FileFormat.BINARY,
        content_type_override="application/octet-stream",
    )
