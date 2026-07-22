import numpy as np
import pytest

from rainroute_data.parsers.radar_binary import RadarGrid
from rainroute_data.parsers.radar_latlon import (
    RadarCoordinateGrid,
)
from rainroute_data.validation.radar_grid import (
    RadarGridAlignmentError,
    validate_radar_grid_alignment,
)


def radar_grid(
    shape: tuple[int, int],
) -> RadarGrid:
    ny, nx = shape

    return RadarGrid(
        nx=nx,
        ny=ny,
        values=np.zeros(shape, dtype=np.int16),
        byte_order="little",
    )


def coordinate_grid(
    values: np.ndarray,
) -> RadarCoordinateGrid:
    ny, nx = values.shape

    return RadarCoordinateGrid(
        nx=nx,
        ny=ny,
        values=values.astype(np.float32),
        byte_order="little",
    )


def test_validate_radar_grid_alignment() -> None:
    lat = np.array(
        [
            [36.0, 36.0, 36.0],
            [36.5, 36.5, 36.5],
            [37.0, 37.0, 37.0],
        ],
        dtype=np.float32,
    )

    lon = np.array(
        [
            [126.0, 126.5, 127.0],
            [126.0, 126.5, 127.0],
            [126.0, 126.5, 127.0],
        ],
        dtype=np.float32,
    )

    report = validate_radar_grid_alignment(
        radar_grid((3, 3)),
        coordinate_grid(lat),
        coordinate_grid(lon),
    )

    assert report.shape == (3, 3)
    assert report.latitude_min == pytest.approx(36.0)
    assert report.latitude_max == pytest.approx(37.0)
    assert report.longitude_min == pytest.approx(126.0)
    assert report.longitude_max == pytest.approx(127.0)
    assert report.longitude_x_positive_fraction == 1.0
    assert report.latitude_y_positive_fraction == 1.0


def test_rejects_shape_mismatch() -> None:
    lat = coordinate_grid(
        np.zeros((2, 2), dtype=np.float32)
    )
    lon = coordinate_grid(
        np.zeros((3, 3), dtype=np.float32)
    )

    with pytest.raises(
        RadarGridAlignmentError,
        match="Latitude shape",
    ):
        validate_radar_grid_alignment(
            radar_grid((3, 3)),
            lat,
            lon,
        )


def test_rejects_reversed_longitude_axis() -> None:
    lat = coordinate_grid(
        np.array(
            [
                [36.0, 36.0],
                [37.0, 37.0],
            ],
            dtype=np.float32,
        )
    )

    lon = coordinate_grid(
        np.array(
            [
                [127.0, 126.0],
                [127.0, 126.0],
            ],
            dtype=np.float32,
        )
    )

    with pytest.raises(
        RadarGridAlignmentError,
        match="Longitude does not predominantly increase",
    ):
        validate_radar_grid_alignment(
            radar_grid((2, 2)),
            lat,
            lon,
        )
