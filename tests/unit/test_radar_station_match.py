import numpy as np
import pytest

from rainroute_data.parsers.radar_latlon import (
    RadarCoordinateGrid,
)
from rainroute_data.validation.radar_station_match import (
    nearest_radar_cell,
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


def test_nearest_radar_cell() -> None:
    latitude = coordinate_grid(
        np.array(
            [
                [37.0, 37.0],
                [37.1, 37.1],
            ]
        )
    )
    longitude = coordinate_grid(
        np.array(
            [
                [127.0, 127.1],
                [127.0, 127.1],
            ]
        )
    )

    match = nearest_radar_cell(
        station_latitude=37.09,
        station_longitude=127.09,
        latitude=latitude,
        longitude=longitude,
    )

    assert match.y == 1
    assert match.x == 1
    assert match.distance_km < 2.0
    assert match.grid_latitude == pytest.approx(37.1)
    assert match.grid_longitude == pytest.approx(127.1)
