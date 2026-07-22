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

HSP_FILE_ENDPOINT = "/api/typ04/url/rdr_cmp_file.php"


def collect_hsp_file(
    *,
    collector: RawResponseCollector,
    data_root: Path,
    valid_time: datetime,
) -> CollectionManifest:
    if valid_time.tzinfo is None:
        raise ValueError("valid_time must be timezone-aware")

    valid_time_kst = valid_time.astimezone(KST)

    identity = DataIdentity(
        source="radar_hsp",
        product="HSP",
        valid_time=valid_time_kst,
        variable="rain_rate",
        grid="HSP_native",
    )

    destination = raw_artifact_path(
        data_root,
        identity,
        suffix="bin",
    )

    return collector.collect(
        identity=identity,
        endpoint=HSP_FILE_ENDPOINT,
        params={
            "tm": valid_time_kst.strftime("%Y%m%d%H%M"),
            "data": "bin",
            "cmp": "hsp",
        },
        destination=destination,
        file_format=FileFormat.BINARY,
        content_type_override="application/octet-stream",
    )
