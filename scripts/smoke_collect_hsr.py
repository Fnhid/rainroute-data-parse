from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.radar_hsr import (
    collect_hsr_grid,
)
from rainroute_data.collectors.raw_response import (
    RawResponseCollector,
)
from rainroute_data.parsers.radar_binary import (
    hsr_to_dbz,
    parse_radar_binary_file,
)
from rainroute_data.schemas.manifest import DataIdentity
from rainroute_data.storage.layout import raw_artifact_path

KST = ZoneInfo("Asia/Seoul")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--time",
        required=True,
        help="HSR observation time in KST: YYYYMMDDHHMM",
    )
    parser.add_argument(
        "--qcd",
        default="MSK",
        choices=("KMA", "NQC", "EXT", "MSK"),
    )
    parser.add_argument(
        "--map",
        dest="map_code",
        default="HB",
        choices=("HB", "HR", "HC"),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = os.environ.get("KMA_API_KEY")
    data_root_text = os.environ.get(
        "RAINROUTE_DATA_ROOT"
    )

    if not api_key:
        raise SystemExit("KMA_API_KEY is not set")

    if not data_root_text:
        raise SystemExit(
            "RAINROUTE_DATA_ROOT is not set"
        )

    data_root = Path(data_root_text).expanduser().resolve()

    valid_time = datetime.strptime(
        args.time,
        "%Y%m%d%H%M",
    ).replace(tzinfo=KST)

    with KmaClient(api_key=api_key) as client:
        raw_collector = RawResponseCollector(
            client=client,
            data_root=data_root,
        )

        manifest = collect_hsr_grid(
            collector=raw_collector,
            data_root=data_root,
            valid_time=valid_time,
            qcd=args.qcd,
            map_code=args.map_code,
        )

    identity = DataIdentity(
        source="radar_hsr",
        product="HSR",
        valid_time=valid_time,
        variable="reflectivity",
        grid=f"{args.map_code}_500m",
    )

    artifact_path = raw_artifact_path(
        data_root,
        identity,
        suffix="bin",
    )

    grid = parse_radar_binary_file(artifact_path)
    dbz = hsr_to_dbz(grid.values)

    print(f"status={manifest.status}")
    print(f"path={artifact_path}")
    print(f"shape={grid.shape}")
    print(f"byte_order={grid.byte_order}")
    print(f"raw_min={grid.values.min()}")
    print(f"raw_max={grid.values.max()}")
    print(
        "finite_dbz_count="
        f"{int(np.isfinite(dbz).sum())}"
    )
    print(
        "file_size_bytes="
        f"{artifact_path.stat().st_size}"
    )
    print(
        "sha256="
        f"{manifest.artifact.sha256 if manifest.artifact else None}"
    )


if __name__ == "__main__":
    main()
