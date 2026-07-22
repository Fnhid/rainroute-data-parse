from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.aws_minute import (
    aws_minute_path,
    collect_aws_minute,
)
from rainroute_data.collectors.radar_hsp_aws_points import (
    collect_hsp_aws_points,
    hsp_aws_points_path,
)
from rainroute_data.collectors.raw_response import RawResponseCollector
from rainroute_data.datasets.hsp_aws_calibration import (
    build_hsp_aws_calibration_rows,
    write_hsp_aws_calibration_csv,
)

KST = ZoneInfo("Asia/Seoul")


def parse_kst(value: str) -> datetime:
    return datetime.strptime(
        value,
        "%Y%m%d%H%M",
    ).replace(tzinfo=KST)


def iter_times(
    start: datetime,
    end: datetime,
    interval_minutes: int,
):
    current = start

    while current <= end:
        yield current
        current += timedelta(minutes=interval_minutes)


def calibration_output_path(
    data_root: Path,
    *,
    target_time: datetime,
    quality_code: str,
) -> Path:
    return (
        data_root
        / "processed"
        / "hsp_aws_calibration"
        / f"{target_time:%Y}"
        / f"{target_time:%m}"
        / f"{target_time:%d}"
        / (
            f"HSP_AWS_CALIBRATION_"
            f"{target_time:%Y%m%dT%H%M%S%z}_"
            f"{quality_code}.csv"
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start",
        required=True,
        help="First calibration target in KST: YYYYMMDDHHMM",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="Last calibration target in KST: YYYYMMDDHHMM",
    )
    parser.add_argument(
        "--interval",
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

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = os.environ.get("KMA_API_KEY")
    data_root_text = os.environ.get("RAINROUTE_DATA_ROOT")

    if not api_key:
        raise SystemExit("KMA_API_KEY is not set")

    if not data_root_text:
        raise SystemExit("RAINROUTE_DATA_ROOT is not set")

    if args.interval <= 0:
        raise SystemExit("--interval must be positive")

    start = parse_kst(args.start)
    end = parse_kst(args.end)

    if end < start:
        raise SystemExit("--end must not be earlier than --start")

    data_root = Path(data_root_text).expanduser().resolve()
    quality_code = args.quality_code.upper()

    target_times = list(
        iter_times(
            start,
            end,
            args.interval,
        )
    )

    # Each 15-minute calibration window requires:
    # target-15, target-10, target-5, target.
    hsp_start = start - timedelta(minutes=15)
    hsp_times = list(
        iter_times(
            hsp_start,
            end,
            5,
        )
    )

    collection_failures = 0
    build_failures = 0
    total_rows = 0
    total_wet_rows = 0

    with KmaClient(api_key=api_key) as client:
        collector = RawResponseCollector(
            client=client,
            data_root=data_root,
        )

        print("[collect_hsp_points]")

        for valid_time in hsp_times:
            destination = hsp_aws_points_path(
                data_root,
                valid_time=valid_time,
                quality_code=quality_code,
            )

            if destination.exists():
                print(
                    f"time={valid_time:%Y%m%d%H%M} "
                    "status=reused"
                )
                continue

            try:
                manifest = collect_hsp_aws_points(
                    collector=collector,
                    data_root=data_root,
                    valid_time=valid_time,
                    quality_code=quality_code,
                    include_help=True,
                )

                print(
                    f"time={valid_time:%Y%m%d%H%M} "
                    f"status={manifest.status}"
                )
            except Exception as exc:
                collection_failures += 1

                print(
                    f"time={valid_time:%Y%m%d%H%M} "
                    f"status=failed "
                    f"error={type(exc).__name__}: {exc}"
                )

        print()
        print("[collect_aws_and_build]")

        for target_time in target_times:
            try:
                aws_path = aws_minute_path(
                    data_root,
                    start_time=target_time,
                    end_time=target_time,
                    station_id=0,
                )

                if aws_path.exists():
                    aws_status = "reused"
                else:
                    aws_manifest = collect_aws_minute(
                        collector=collector,
                        data_root=data_root,
                        start_time=target_time,
                        end_time=target_time,
                        station_id=0,
                        include_help=True,
                    )
                    aws_status = str(aws_manifest.status)

                rows = build_hsp_aws_calibration_rows(
                    target_time=target_time,
                    aws_file=aws_path,
                    data_root=data_root,
                    quality_code=quality_code,
                    wet_threshold_mm=args.wet_threshold_mm,
                )

                output = calibration_output_path(
                    data_root,
                    target_time=target_time,
                    quality_code=quality_code,
                )

                write_hsp_aws_calibration_csv(
                    rows,
                    output,
                )

                errors = np.array(
                    [row.error_mm for row in rows],
                    dtype=np.float64,
                )

                wet_rows = sum(
                    row.hsp_wet or row.aws_wet
                    for row in rows
                )

                total_rows += len(rows)
                total_wet_rows += wet_rows

                print(
                    f"time={target_time:%Y%m%d%H%M} "
                    f"aws_status={aws_status} "
                    f"rows={len(rows)} "
                    f"wet_rows={wet_rows} "
                    f"mae_mm={np.abs(errors).mean():.6f} "
                    f"bias_mm={errors.mean():+.6f} "
                    f"output={output}"
                )

            except Exception as exc:
                build_failures += 1

                print(
                    f"time={target_time:%Y%m%d%H%M} "
                    f"status=failed "
                    f"error={type(exc).__name__}: {exc}"
                )

    print()
    print("[summary]")
    print(f"target_count={len(target_times)}")
    print(f"hsp_time_count={len(hsp_times)}")
    print(f"total_rows={total_rows}")
    print(f"total_wet_rows={total_wet_rows}")
    print(f"collection_failures={collection_failures}")
    print(f"build_failures={build_failures}")

    if collection_failures or build_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
