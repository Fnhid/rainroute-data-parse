from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

SINGLE_TARGET_PATTERN = re.compile(
    r"^HSP_AWS_CALIBRATION_"
    r"\d{8}T\d{6}[+-]\d{4}_[A-Z]+\.csv$"
)

KEY_COLUMNS = [
    "target_time_kst",
    "station_id",
    "quality_code",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    files = sorted(
        path
        for path in args.input_dir.glob("*.csv")
        if SINGLE_TARGET_PATTERN.fullmatch(path.name)
    )

    if not files:
        raise SystemExit(
            f"No single-target calibration CSV files found in "
            f"{args.input_dir}"
        )

    frames = [
        pd.read_csv(path).assign(
            source_file=path.name
        )
        for path in files
    ]

    data = pd.concat(
        frames,
        ignore_index=True,
    )

    duplicate_mask = data.duplicated(
        KEY_COLUMNS,
        keep=False,
    )
    duplicate_count = int(
        data.duplicated(KEY_COLUMNS).sum()
    )

    if duplicate_count:
        print("[duplicate_examples]")
        print(
            data.loc[
                duplicate_mask,
                KEY_COLUMNS + ["source_file"],
            ]
            .sort_values(KEY_COLUMNS)
            .head(50)
            .to_string(index=False)
        )

        raise SystemExit(
            f"Duplicate calibration keys found: "
            f"{duplicate_count}"
        )

    wet_mask = (
        data["hsp_wet"]
        | data["aws_wet"]
    )
    wet_data = data.loc[wet_mask]

    print(f"file_count={len(files)}")
    print(f"row_count={len(data)}")
    print(
        "unique_target_times="
        f"{data['target_time_kst'].nunique()}"
    )
    print(
        "unique_stations="
        f"{data['station_id'].nunique()}"
    )
    print("duplicate_key_count=0")
    print(
        f"wet_row_count={int(wet_mask.sum())}"
    )

    print()
    print("[all]")
    print(
        "mae_mm="
        f"{data['absolute_error_mm'].mean():.8f}"
    )
    print(
        "bias_mm="
        f"{data['error_mm'].mean():.8f}"
    )
    print(
        "p95_ae_mm="
        f"{data['absolute_error_mm'].quantile(0.95):.8f}"
    )

    if not wet_data.empty:
        correlation = wet_data[
            "hsp_accumulation_15m_mm"
        ].corr(
            wet_data[
                "aws_accumulation_15m_mm"
            ]
        )

        print()
        print("[either_wet]")
        print(f"count={len(wet_data)}")
        print(
            "mae_mm="
            f"{wet_data['absolute_error_mm'].mean():.8f}"
        )
        print(
            "bias_mm="
            f"{wet_data['error_mm'].mean():.8f}"
        )
        print(
            f"pearson_r={correlation:.8f}"
        )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = args.output.with_suffix(
        args.output.suffix + ".tmp"
    )

    data.sort_values(
        KEY_COLUMNS
    ).to_csv(
        temporary,
        index=False,
    )

    temporary.replace(args.output)

    print()
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
