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

AWS_MINUTE_ENDPOINT = (
    "/api/typ01/cgi-bin/url/nph-aws2_min"
)


def aws_minute_path(
    data_root: Path,
    *,
    start_time: datetime,
    end_time: datetime,
    station_id: int,
) -> Path:
    start_kst = start_time.astimezone(KST)
    end_kst = end_time.astimezone(KST)

    filename = (
        f"AWS_{start_kst:%Y%m%dT%H%M%S%z}"
        f"_{end_kst:%Y%m%dT%H%M%S%z}"
        f"_stn-{station_id}.csv"
    )

    return (
        data_root.expanduser().resolve()
        / "raw"
        / "aws_minute"
        / f"{start_kst:%Y}"
        / f"{start_kst:%m}"
        / f"{start_kst:%d}"
        / filename
    )


def collect_aws_minute(
    *,
    collector: RawResponseCollector,
    data_root: Path,
    start_time: datetime,
    end_time: datetime,
    station_id: int = 0,
    include_help: bool = True,
) -> CollectionManifest:
    if start_time.tzinfo is None:
        raise ValueError("start_time must be timezone-aware")

    if end_time.tzinfo is None:
        raise ValueError("end_time must be timezone-aware")

    start_kst = start_time.astimezone(KST)
    end_kst = end_time.astimezone(KST)

    if end_kst < start_kst:
        raise ValueError("end_time must not be earlier than start_time")

    duration_minutes = int(
        (end_kst - start_kst).total_seconds() / 60
    )

    if station_id == 0 and duration_minutes > 10:
        raise ValueError(
            "All-station AWS requests must not exceed 10 minutes"
        )

    identity = DataIdentity(
        source="aws_minute",
        product="AWS",
        valid_time=end_kst,
        variable="surface_observation",
        grid="station",
    )

    destination = aws_minute_path(
        data_root,
        start_time=start_kst,
        end_time=end_kst,
        station_id=station_id,
    )

    return collector.collect(
        identity=identity,
        endpoint=AWS_MINUTE_ENDPOINT,
        params={
            "tm1": start_kst.strftime("%Y%m%d%H%M"),
            "tm2": end_kst.strftime("%Y%m%d%H%M"),
            "stn": station_id,
            "disp": 1,
            "help": 1 if include_help else 2,
        },
        destination=destination,
        file_format=FileFormat.TEXT,
        content_type_override="text/plain; charset=utf-8",
    )
