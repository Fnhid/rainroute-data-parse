from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from rainroute_data.parsers.radar_hsp import parse_hsp_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    grid = parse_hsp_file(args.path)
    values = grid.values

    special = np.isin(
        values,
        (-20_000, -25_000, -30_000),
    )
    physical = values[~special]

    print(f"path={args.path}")
    print(f"shape={grid.shape}")
    print(f"physical_count={physical.size}")
    print(f"raw_min={physical.min()}")
    print(f"raw_max={physical.max()}")

    for scale in (1.0, 0.1, 0.01, 0.001):
        converted = physical.astype(np.float64) * scale

        print()
        print(f"scale={scale}")
        print(f"min={converted.min():.6f}")
        print(f"median={np.median(converted):.6f}")
        print(f"p90={np.percentile(converted, 90):.6f}")
        print(f"p99={np.percentile(converted, 99):.6f}")
        print(f"max={converted.max():.6f}")


if __name__ == "__main__":
    main()
