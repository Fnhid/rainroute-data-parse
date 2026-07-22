from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from rainroute_data.parsers.radar_binary import RadarGrid
from rainroute_data.parsers.radar_latlon import RadarCoordinateGrid


class RadarGridAlignmentError(ValueError):
    """Raised when radar values and coordinate grids are inconsistent."""


@dataclass(frozen=True)
class RadarGridAlignmentReport:
    shape: tuple[int, int]
    finite_coordinate_cells: int
    total_cells: int
    latitude_min: float
    latitude_max: float
    longitude_min: float
    longitude_max: float
    longitude_x_positive_fraction: float
    latitude_y_positive_fraction: float
    median_longitude_x_step: float
    median_latitude_y_step: float

    @property
    def finite_coordinate_fraction(self) -> float:
        return self.finite_coordinate_cells / self.total_cells


def _positive_fraction(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]

    if finite.size == 0:
        return 0.0

    return float((finite > 0).sum() / finite.size)


def validate_radar_grid_alignment(
    values: RadarGrid,
    latitude: RadarCoordinateGrid,
    longitude: RadarCoordinateGrid,
    *,
    minimum_latitude: float = 20.0,
    maximum_latitude: float = 50.0,
    minimum_longitude: float = 110.0,
    maximum_longitude: float = 150.0,
    minimum_axis_positive_fraction: float = 0.95,
) -> RadarGridAlignmentReport:
    expected_shape = values.shape

    if latitude.shape != expected_shape:
        raise RadarGridAlignmentError(
            "Latitude shape does not match radar values: "
            f"radar={expected_shape}, latitude={latitude.shape}"
        )

    if longitude.shape != expected_shape:
        raise RadarGridAlignmentError(
            "Longitude shape does not match radar values: "
            f"radar={expected_shape}, longitude={longitude.shape}"
        )

    if latitude.nx != values.nx or latitude.ny != values.ny:
        raise RadarGridAlignmentError(
            "Latitude header dimensions do not match radar values"
        )

    if longitude.nx != values.nx or longitude.ny != values.ny:
        raise RadarGridAlignmentError(
            "Longitude header dimensions do not match radar values"
        )

    lat = latitude.values
    lon = longitude.values

    finite = np.isfinite(lat) & np.isfinite(lon)

    if not np.all(finite):
        missing = int((~finite).sum())
        raise RadarGridAlignmentError(
            f"Coordinate grids contain {missing} non-finite cells"
        )

    latitude_min = float(lat.min())
    latitude_max = float(lat.max())
    longitude_min = float(lon.min())
    longitude_max = float(lon.max())

    if not (
        minimum_latitude
        <= latitude_min
        <= latitude_max
        <= maximum_latitude
    ):
        raise RadarGridAlignmentError(
            "Latitude range is outside the configured domain: "
            f"min={latitude_min}, max={latitude_max}"
        )

    if not (
        minimum_longitude
        <= longitude_min
        <= longitude_max
        <= maximum_longitude
    ):
        raise RadarGridAlignmentError(
            "Longitude range is outside the configured domain: "
            f"min={longitude_min}, max={longitude_max}"
        )

    longitude_x_difference = np.diff(lon, axis=1)
    latitude_y_difference = np.diff(lat, axis=0)

    longitude_x_positive_fraction = _positive_fraction(
        longitude_x_difference
    )
    latitude_y_positive_fraction = _positive_fraction(
        latitude_y_difference
    )

    if (
        longitude_x_positive_fraction
        < minimum_axis_positive_fraction
    ):
        raise RadarGridAlignmentError(
            "Longitude does not predominantly increase along x: "
            f"positive_fraction={longitude_x_positive_fraction:.6f}"
        )

    if (
        latitude_y_positive_fraction
        < minimum_axis_positive_fraction
    ):
        raise RadarGridAlignmentError(
            "Latitude does not predominantly increase along y: "
            f"positive_fraction={latitude_y_positive_fraction:.6f}"
        )

    return RadarGridAlignmentReport(
        shape=expected_shape,
        finite_coordinate_cells=int(finite.sum()),
        total_cells=int(finite.size),
        latitude_min=latitude_min,
        latitude_max=latitude_max,
        longitude_min=longitude_min,
        longitude_max=longitude_max,
        longitude_x_positive_fraction=(
            longitude_x_positive_fraction
        ),
        latitude_y_positive_fraction=(
            latitude_y_positive_fraction
        ),
        median_longitude_x_step=float(
            np.median(longitude_x_difference)
        ),
        median_latitude_y_step=float(
            np.median(latitude_y_difference)
        ),
    )
