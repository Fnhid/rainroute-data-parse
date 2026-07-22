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

KST = ZoneInfo("Asia/Seoul")

HSP_AWS_ALL_POINT_ENDPOINT = (
    "/api/typ01/cgi-bin/url/"
    "nph-rdr_cmp_aws_all_pt_data"
)


def hsp_aws_points_path(
    data_root: Path,
    *,
    valid_time: datetime,
    quality_code: str = "EXT",
) -> Path:
    if valid_time.tzinfo is None:
        raise ValueError("valid_time must be timezone-aware")

    valid_kst = valid_time.astimezone(KST)
    quality_code = quality_code.upper()

    return (
        data_root.expanduser().resolve()
        / "raw"
        / "radar_hsp_aws_points"
        / f"{valid_kst:%Y}"
        / f"{valid_kst:%m}"
        / f"{valid_kst:%d}"
        / (
            f"HSP_AWS_{valid_kst:%Y%m%dT%H%M%S%z}"
            f"_{quality_code}.txt"
        )
    )


def collect_hsp_aws_points(
    *,
    collector: RawResponseCollector,
    data_root: Path,
    valid_time: datetime,
    quality_code: str = "EXT",
    include_help: bool = True,
) -> CollectionManifest:
    if valid_time.tzinfo is None:
        raise ValueError("valid_time must be timezone-aware")

    quality_code = quality_code.upper()

    if quality_code not in {"KMA", "EXT", "MSK"}:
        raise ValueError(
            "quality_code must be one of: KMA, EXT, MSK"
        )

    valid_kst = valid_time.astimezone(KST)

    identity = DataIdentity(
        source="radar_hsp_aws_points",
        product="HSP",
        valid_time=valid_kst,
        variable="rain_rate",
        grid="aws_station",
    )

    return collector.collect(
        identity=identity,
        endpoint=HSP_AWS_ALL_POINT_ENDPOINT,
        params={
            "tm": valid_kst.strftime("%Y%m%d%H%M"),
            "qcd": quality_code,
            "cmp": "HSP",
            "help": 1 if include_help else 0,
        },
        destination=hsp_aws_points_path(
            data_root,
            valid_time=valid_kst,
            quality_code=quality_code,
        ),
        file_format=FileFormat.TEXT,
        content_type_override="text/plain; charset=cp949",
    )
