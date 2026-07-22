from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.radar_hsp_aws_points import (
    collect_hsp_aws_points,
    hsp_aws_points_path,
)
from rainroute_data.collectors.raw_response import RawResponseCollector
from rainroute_data.parsers.radar_hsp_aws_points import (
    parse_hsp_aws_points_file,
)

KST = ZoneInfo("Asia/Seoul")


def parse_time(value: str) -> datetime:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start",
        required=True,
        help="Start time in KST: YYYYMMDDHHMM",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End time in KST: YYYYMMDDHHMM",
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

    data_root = Path(data_root_text).expanduser().resolve()

    start = parse_time(args.start)
    end = parse_time(args.end)

    if end < start:
        raise SystemExit("--end must not be earlier than --start")

    success_count = 0
    duplicate_count = 0
    failure_count = 0

    with KmaClient(api_key=api_key) as client:
        collector = RawResponseCollector(
            client=client,
            data_root=data_root,
        )

        for valid_time in iter_times(
            start,
            end,
            args.interval,
        ):
            try:
                manifest = collect_hsp_aws_points(
                    collector=collector,
                    data_root=data_root,
                    valid_time=valid_time,
                    quality_code=args.quality_code,
                    include_help=True,
                )

                path = hsp_aws_points_path(
                    data_root,
                    valid_time=valid_time,
                    quality_code=args.quality_code,
                )

                points = parse_hsp_aws_points_file(path)

                physical_count = sum(
                    point.status == "physical"
                    for point in points
                )

                print(
                    f"time={valid_time:%Y%m%d%H%M} "
                    f"status={manifest.status} "
                    f"points={len(points)} "
                    f"physical={physical_count}"
                )

                status = str(manifest.status)

                if status == "success":
                    success_count += 1
                elif status == "duplicate":
                    duplicate_count += 1
                else:
                    failure_count += 1

            except Exception as exc:
                failure_count += 1

                print(
                    f"time={valid_time:%Y%m%d%H%M} "
                    f"status=failed "
                    f"error={type(exc).__name__}: {exc}"
                )

    print()
    print(f"success_count={success_count}")
    print(f"duplicate_count={duplicate_count}")
    print(f"failure_count={failure_count}")

    if failure_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
