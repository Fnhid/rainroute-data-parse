from __future__ import annotations

import os
from pathlib import Path

from rainroute_data.collectors.radar_latlon import radar_latlon_path
from rainroute_data.parsers.radar_hsp import parse_hsp_file
from rainroute_data.parsers.radar_latlon import parse_radar_latlon_file
from rainroute_data.validation.radar_grid import (
    validate_radar_grid_alignment,
)


def latest_hsp_file(data_root: Path) -> Path:
    candidates = sorted(
        (data_root / "raw" / "radar_hsp").rglob("*.bin")
    )

    if not candidates:
        raise SystemExit("No HSP binary file was found")

    return candidates[-1]


def main() -> None:
    data_root_text = os.environ.get("RAINROUTE_DATA_ROOT")

    if not data_root_text:
        raise SystemExit("RAINROUTE_DATA_ROOT is not set")

    data_root = Path(data_root_text).expanduser().resolve()

    hsp_path_text = os.environ.get("RAINROUTE_HSP_SMOKE_FILE")

    hsp_path = (
        Path(hsp_path_text).expanduser().resolve()
        if hsp_path_text
        else latest_hsp_file(data_root)
    )

    latitude_path = radar_latlon_path(
        data_root,
        product="HSP",
        coordinate="lat",
    )
    longitude_path = radar_latlon_path(
        data_root,
        product="HSP",
        coordinate="lon",
    )

    hsp = parse_hsp_file(hsp_path)
    latitude = parse_radar_latlon_file(latitude_path)
    longitude = parse_radar_latlon_file(longitude_path)

    report = validate_radar_grid_alignment(
        hsp,
        latitude,
        longitude,
    )

    print(f"hsp_path={hsp_path}")
    print(f"latitude_path={latitude_path}")
    print(f"longitude_path={longitude_path}")
    print(f"hsp_shape={hsp.shape}")
    print(f"latitude_shape={latitude.shape}")
    print(f"longitude_shape={longitude.shape}")
    print(
        f"latitude_range="
        f"({report.latitude_min:.6f}, "
        f"{report.latitude_max:.6f})"
    )
    print(
        f"longitude_range="
        f"({report.longitude_min:.6f}, "
        f"{report.longitude_max:.6f})"
    )
    print(
        "longitude_x_positive_fraction="
        f"{report.longitude_x_positive_fraction:.8f}"
    )
    print(
        "latitude_y_positive_fraction="
        f"{report.latitude_y_positive_fraction:.8f}"
    )
    print(
        "median_longitude_x_step="
        f"{report.median_longitude_x_step:.10f}"
    )
    print(
        "median_latitude_y_step="
        f"{report.median_latitude_y_step:.10f}"
    )


if __name__ == "__main__":
    main()
