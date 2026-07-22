from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from rainroute_data.collectors.radar_hsp_aws_points import (
    hsp_aws_points_path,
)
from rainroute_data.parsers.aws_minute import (
    parse_aws_minute_file,
)
from rainroute_data.parsers.radar_hsp_aws_points import (
    HspAwsPoint,
    parse_hsp_aws_points_file,
)
from rainroute_data.validation.precipitation_accumulation import (
    trapezoidal_accumulation_mm,
)

KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class Comparison:
    station_id: int
    hsp_accumulation_mm: float
    aws_accumulation_mm: float
    error_mm: float
    absolute_error_mm: float
    hsp_rates_mm_h: tuple[float, ...]


def parse_kst(value: str) -> datetime:
    return datetime.strptime(
        value,
        "%Y%m%d%H%M",
    ).replace(tzinfo=KST)


def sample_times(
    *,
    target_time: datetime,
    window_minutes: int,
    interval_minutes: int,
) -> list[datetime]:
    if window_minutes <= 0:
        raise ValueError("window_minutes must be positive")

    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be positive")

    if window_minutes % interval_minutes != 0:
        raise ValueError(
            "window_minutes must be divisible by interval_minutes"
        )

    sample_count = window_minutes // interval_minutes

    start_time = target_time - timedelta(
        minutes=window_minutes
    )

    return [
        start_time + timedelta(
            minutes=index * interval_minutes
        )
        for index in range(sample_count + 1)
    ]


def point_rate_mm_h(point: HspAwsPoint) -> float | None:
    if point.status == "physical":
        return point.echo_mm_h

    if point.status == "no_rain":
        return 0.0

    return None


def point_map(path: Path) -> dict[int, HspAwsPoint]:
    points = parse_hsp_aws_points_file(path)

    return {
        point.station_id: point
        for point in points
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--target-time",
        required=True,
        help="End of accumulation window in KST: YYYYMMDDHHMM",
    )
    parser.add_argument(
        "--aws-file",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=15,
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--quality-code",
        default="EXT",
        choices=("KMA", "EXT", "MSK"),
    )
    parser.add_argument(
        "--wet-threshold-mm",
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
    )

    return parser.parse_args()


def print_metrics(
    name: str,
    rows: list[Comparison],
) -> None:
    print()
    print(f"[{name}]")
    print(f"count={len(rows)}")

    if not rows:
        return

    hsp = np.array(
        [row.hsp_accumulation_mm for row in rows],
        dtype=np.float64,
    )
    aws = np.array(
        [row.aws_accumulation_mm for row in rows],
        dtype=np.float64,
    )

    errors = hsp - aws
    absolute_errors = np.abs(errors)

    print(f"mae_mm={absolute_errors.mean():.8f}")
    print(f"median_ae_mm={np.median(absolute_errors):.8f}")
    print(f"p90_ae_mm={np.percentile(absolute_errors, 90):.8f}")
    print(f"p95_ae_mm={np.percentile(absolute_errors, 95):.8f}")
    print(f"max_ae_mm={absolute_errors.max():.8f}")
    print(f"mean_bias_mm={errors.mean():.8f}")
    print(f"hsp_mean_mm={hsp.mean():.8f}")
    print(f"aws_mean_mm={aws.mean():.8f}")

    if (
        len(rows) >= 2
        and np.std(hsp) > 0
        and np.std(aws) > 0
    ):
        correlation = float(
            np.corrcoef(hsp, aws)[0, 1]
        )
        print(f"pearson_r={correlation:.8f}")
    else:
        print("pearson_r=nan")


def main() -> None:
    args = parse_args()

    target_time = parse_kst(args.target_time)
    times = sample_times(
        target_time=target_time,
        window_minutes=args.window_minutes,
        interval_minutes=args.interval_minutes,
    )

    print(
        "sample_times="
        + ",".join(
            time.strftime("%Y%m%d%H%M")
            for time in times
        )
    )

    point_maps: list[dict[int, HspAwsPoint]] = []

    for valid_time in times:
        path = hsp_aws_points_path(
            args.data_root,
            valid_time=valid_time,
            quality_code=args.quality_code,
        )

        if not path.exists():
            raise SystemExit(
                f"Missing HSP AWS-point file: {path}"
            )

        points = point_map(path)
        point_maps.append(points)

        print(
            f"hsp_time={valid_time:%Y%m%d%H%M} "
            f"station_count={len(points)} "
            f"path={path}"
        )

    aws_observations = parse_aws_minute_file(
        args.aws_file
    )

    aws_at_target = {
        observation.station_id: observation
        for observation in aws_observations
        if observation.observed_at.strftime("%Y%m%d%H%M")
        == target_time.strftime("%Y%m%d%H%M")
        and observation.rain_15m_mm is not None
    }

    common_station_ids = set(aws_at_target)

    for points in point_maps:
        common_station_ids &= set(points)

    comparisons: list[Comparison] = []
    excluded_unusable_hsp = 0

    for station_id in sorted(common_station_ids):
        rates: list[float] = []

        for points in point_maps:
            rate = point_rate_mm_h(points[station_id])

            if rate is None:
                rates = []
                break

            rates.append(rate)

        if not rates:
            excluded_unusable_hsp += 1
            continue

        hsp_accumulation = trapezoidal_accumulation_mm(
            rates,
            interval_minutes=args.interval_minutes,
        )
        aws_accumulation = aws_at_target[
            station_id
        ].rain_15m_mm

        if aws_accumulation is None:
            continue

        error = hsp_accumulation - aws_accumulation

        comparisons.append(
            Comparison(
                station_id=station_id,
                hsp_accumulation_mm=hsp_accumulation,
                aws_accumulation_mm=aws_accumulation,
                error_mm=error,
                absolute_error_mm=abs(error),
                hsp_rates_mm_h=tuple(rates),
            )
        )

    print()
    print(f"aws_target_count={len(aws_at_target)}")
    print(f"common_station_count={len(common_station_ids)}")
    print(f"excluded_unusable_hsp={excluded_unusable_hsp}")
    print(f"comparison_count={len(comparisons)}")

    wet_threshold = args.wet_threshold_mm

    aws_wet = [
        row
        for row in comparisons
        if row.aws_accumulation_mm >= wet_threshold
    ]
    hsp_wet = [
        row
        for row in comparisons
        if row.hsp_accumulation_mm >= wet_threshold
    ]
    either_wet = [
        row
        for row in comparisons
        if (
            row.aws_accumulation_mm >= wet_threshold
            or row.hsp_accumulation_mm >= wet_threshold
        )
    ]
    both_wet = [
        row
        for row in comparisons
        if (
            row.aws_accumulation_mm >= wet_threshold
            and row.hsp_accumulation_mm >= wet_threshold
        )
    ]

    print_metrics("all", comparisons)
    print_metrics("aws_wet", aws_wet)
    print_metrics("hsp_wet", hsp_wet)
    print_metrics("either_wet", either_wet)
    print_metrics("both_wet", both_wet)

    aws_wet_ids = {
        row.station_id
        for row in aws_wet
    }
    hsp_wet_ids = {
        row.station_id
        for row in hsp_wet
    }

    hits = len(aws_wet_ids & hsp_wet_ids)
    misses = len(aws_wet_ids - hsp_wet_ids)
    false_alarms = len(hsp_wet_ids - aws_wet_ids)
    correct_negatives = (
        len(comparisons)
        - hits
        - misses
        - false_alarms
    )

    print()
    print("[wet_detection]")
    print(f"threshold_mm={wet_threshold:.3f}")
    print(f"hits={hits}")
    print(f"misses={misses}")
    print(f"false_alarms={false_alarms}")
    print(f"correct_negatives={correct_negatives}")

    if hits + misses:
        print(
            "probability_of_detection="
            f"{hits / (hits + misses):.8f}"
        )

    if hits + false_alarms:
        print(
            "success_ratio="
            f"{hits / (hits + false_alarms):.8f}"
        )

    ranked = sorted(
        comparisons,
        key=lambda row: row.absolute_error_mm,
        reverse=True,
    )

    print()
    print("[largest_errors]")

    for row in ranked[: args.limit]:
        rates_text = ",".join(
            f"{rate:.2f}"
            for rate in row.hsp_rates_mm_h
        )

        print(
            f"stn={row.station_id:4d} "
            f"hsp_15m={row.hsp_accumulation_mm:7.3f} "
            f"aws_15m={row.aws_accumulation_mm:7.3f} "
            f"error={row.error_mm:+7.3f} "
            f"rates=[{rates_text}]"
        )


if __name__ == "__main__":
    main()
