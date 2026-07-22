from __future__ import annotations

import os
from pathlib import Path

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.radar_latlon import (
    collect_radar_latlon_pair,
    radar_latlon_path,
)
from rainroute_data.collectors.raw_response import (
    RawResponseCollector,
)
from rainroute_data.parsers.radar_binary import (
    parse_radar_binary_file,
)
from rainroute_data.parsers.radar_latlon import (
    parse_radar_latlon_file,
)
from rainroute_data.validation.radar_grid import (
    validate_radar_grid_alignment,
)


def main() -> None:
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

    radar_path_text = os.environ.get(
        "RAINROUTE_HSR_SMOKE_FILE"
    )

    if radar_path_text:
        radar_path = Path(
            radar_path_text
        ).expanduser().resolve()
    else:
        candidates = sorted(
            (
                data_root
                / "raw"
                / "radar_hsr"
            ).rglob("*.bin")
        )

        if not candidates:
            raise SystemExit(
                "No collected HSR binary file was found"
            )

        radar_path = candidates[-1]

    with KmaClient(api_key=api_key) as client:
        collector = RawResponseCollector(
            client=client,
            data_root=data_root,
        )

        latitude_manifest, longitude_manifest = (
            collect_radar_latlon_pair(
                collector=collector,
                data_root=data_root,
                product="HSR",
            )
        )

    latitude_path = radar_latlon_path(
        data_root,
        product="HSR",
        coordinate="lat",
    )

    longitude_path = radar_latlon_path(
        data_root,
        product="HSR",
        coordinate="lon",
    )

    radar = parse_radar_binary_file(radar_path)
    latitude = parse_radar_latlon_file(latitude_path)
    longitude = parse_radar_latlon_file(longitude_path)

    report = validate_radar_grid_alignment(
        radar,
        latitude,
        longitude,
    )

    print(f"radar_path={radar_path}")
    print(f"latitude_path={latitude_path}")
    print(f"longitude_path={longitude_path}")
    print(f"latitude_status={latitude_manifest.status}")
    print(f"longitude_status={longitude_manifest.status}")
    print(f"shape={report.shape}")
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
