from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from rainroute_data.collectors.radar_hsp_aws_points import (
    hsp_aws_points_path,
)
from rainroute_data.parsers.aws_minute import parse_aws_minute_file
from rainroute_data.parsers.radar_hsp_aws_points import (
    HspAwsPoint,
    parse_hsp_aws_points_file,
)
from rainroute_data.validation.precipitation_accumulation import (
    trapezoidal_accumulation_mm,
)

KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class HspAwsCalibrationRow:
    target_time_kst: str
    station_id: int
    quality_code: str
    hsp_rate_start_mm_h: float
    hsp_rate_mid1_mm_h: float
    hsp_rate_mid2_mm_h: float
    hsp_rate_end_mm_h: float
    hsp_accumulation_15m_mm: float
    aws_accumulation_15m_mm: float
    error_mm: float
    absolute_error_mm: float
    hsp_wet: bool
    aws_wet: bool


def _point_rate(point: HspAwsPoint) -> float | None:
    if point.status == "physical":
        return point.echo_mm_h

    if point.status == "no_rain":
        return 0.0

    return None


def _point_map(path: Path) -> dict[int, HspAwsPoint]:
    return {
        point.station_id: point
        for point in parse_hsp_aws_points_file(path)
    }


def build_hsp_aws_calibration_rows(
    *,
    target_time: datetime,
    aws_file: Path,
    data_root: Path,
    quality_code: str = "EXT",
    wet_threshold_mm: float = 0.1,
) -> list[HspAwsCalibrationRow]:
    if target_time.tzinfo is None:
        raise ValueError("target_time must be timezone-aware")

    target_kst = target_time.astimezone(KST)

    sample_times = [
        target_kst - timedelta(minutes=15),
        target_kst - timedelta(minutes=10),
        target_kst - timedelta(minutes=5),
        target_kst,
    ]

    point_maps: list[dict[int, HspAwsPoint]] = []

    for valid_time in sample_times:
        path = hsp_aws_points_path(
            data_root,
            valid_time=valid_time,
            quality_code=quality_code,
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Missing HSP AWS-point file: {path}"
            )

        point_maps.append(_point_map(path))

    aws_at_target = {
        observation.station_id: observation
        for observation in parse_aws_minute_file(aws_file)
        if (
            observation.observed_at.strftime("%Y%m%d%H%M")
            == target_kst.strftime("%Y%m%d%H%M")
            and observation.rain_15m_mm is not None
        )
    }

    common_station_ids = set(aws_at_target)

    for points in point_maps:
        common_station_ids &= set(points)

    rows: list[HspAwsCalibrationRow] = []

    for station_id in sorted(common_station_ids):
        rates: list[float] = []

        for points in point_maps:
            rate = _point_rate(points[station_id])

            if rate is None:
                rates = []
                break

            rates.append(rate)

        if len(rates) != 4:
            continue

        aws_accumulation = aws_at_target[
            station_id
        ].rain_15m_mm

        if aws_accumulation is None:
            continue

        hsp_accumulation = trapezoidal_accumulation_mm(
            rates,
            interval_minutes=5,
        )

        error = hsp_accumulation - aws_accumulation

        rows.append(
            HspAwsCalibrationRow(
                target_time_kst=target_kst.strftime(
                    "%Y-%m-%dT%H:%M:%S%z"
                ),
                station_id=station_id,
                quality_code=quality_code,
                hsp_rate_start_mm_h=rates[0],
                hsp_rate_mid1_mm_h=rates[1],
                hsp_rate_mid2_mm_h=rates[2],
                hsp_rate_end_mm_h=rates[3],
                hsp_accumulation_15m_mm=hsp_accumulation,
                aws_accumulation_15m_mm=aws_accumulation,
                error_mm=error,
                absolute_error_mm=abs(error),
                hsp_wet=hsp_accumulation >= wet_threshold_mm,
                aws_wet=aws_accumulation >= wet_threshold_mm,
            )
        )

    return rows


def write_hsp_aws_calibration_csv(
    rows: list[HspAwsCalibrationRow],
    destination: Path,
) -> None:
    if not rows:
        raise ValueError("Calibration table is empty")

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_suffix(
        destination.suffix + ".tmp"
    )

    fieldnames = list(asdict(rows[0]).keys())

    with temporary.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(asdict(row))

        file.flush()

    temporary.replace(destination)
