from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from rainroute_data.datasets.hsp_aws_calibration import (
    build_hsp_aws_calibration_rows,
    write_hsp_aws_calibration_csv,
)

KST = ZoneInfo("Asia/Seoul")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--target-time",
        required=True,
        help="Accumulation end time in KST: YYYYMMDDHHMM",
    )
    parser.add_argument(
        "--aws-file",
        type=Path,
        required=True,
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

    data_root_text = os.environ.get("RAINROUTE_DATA_ROOT")

    if not data_root_text:
        raise SystemExit("RAINROUTE_DATA_ROOT is not set")

    data_root = Path(data_root_text).expanduser().resolve()

    target_time = datetime.strptime(
        args.target_time,
        "%Y%m%d%H%M",
    ).replace(tzinfo=KST)

    output = (
        data_root
        / "processed"
        / "hsp_aws_calibration"
        / f"{target_time:%Y}"
        / f"{target_time:%m}"
        / f"{target_time:%d}"
        / (
            f"HSP_AWS_CALIBRATION_"
            f"{target_time:%Y%m%dT%H%M%S%z}_"
            f"{args.quality_code}.csv"
        )
    )

    rows = build_hsp_aws_calibration_rows(
        target_time=target_time,
        aws_file=args.aws_file,
        data_root=data_root,
        quality_code=args.quality_code,
        wet_threshold_mm=args.wet_threshold_mm,
    )

    write_hsp_aws_calibration_csv(
        rows,
        output,
    )

    errors = np.array(
        [row.error_mm for row in rows],
        dtype=np.float64,
    )

    hits = sum(
        row.hsp_wet and row.aws_wet
        for row in rows
    )
    misses = sum(
        not row.hsp_wet and row.aws_wet
        for row in rows
    )
    false_alarms = sum(
        row.hsp_wet and not row.aws_wet
        for row in rows
    )

    print(f"output={output}")
    print(f"row_count={len(rows)}")
    print(f"mae_mm={np.abs(errors).mean():.8f}")
    print(f"mean_bias_mm={errors.mean():.8f}")
    print(f"hits={hits}")
    print(f"misses={misses}")
    print(f"false_alarms={false_alarms}")


if __name__ == "__main__":
    main()
