import numpy as np
import pytest

from rainroute_data.parsers.radar_binary import (
    HSR_UNDOCUMENTED_MASK,
    RadarGrid,
)
from rainroute_data.validation.radar_hsr import (
    HsrValidationError,
    validate_hsr_grid,
)


def make_grid(values: np.ndarray) -> RadarGrid:
    ny, nx = values.shape

    return RadarGrid(
        nx=nx,
        ny=ny,
        values=values.astype(np.int16),
        byte_order="little",
    )


def test_validate_hsr_grid() -> None:
    grid = make_grid(
        np.array(
            [
                [0, -843, -25_000],
                [500, -30_000, HSR_UNDOCUMENTED_MASK],
            ],
            dtype=np.int16,
        )
    )

    report = validate_hsr_grid(
        grid,
        expected_nx=3,
        expected_ny=2,
    )

    assert report.total_cells == 6
    assert report.physical_cells == 3
    assert report.no_echo_cells == 1
    assert report.outside_cells == 1
    assert report.undocumented_mask_cells == 1
    assert report.negative_physical_cells == 1
    assert report.minimum_physical_raw == -843
    assert report.maximum_physical_raw == 500


def test_rejects_wrong_dimensions() -> None:
    grid = make_grid(np.zeros((2, 3), dtype=np.int16))

    with pytest.raises(
        HsrValidationError,
        match="Unexpected HSR nx",
    ):
        validate_hsr_grid(
            grid,
            expected_nx=4,
            expected_ny=2,
        )


def test_rejects_unknown_extreme_negative_value() -> None:
    grid = make_grid(
        np.array([[-15_000]], dtype=np.int16)
    )

    with pytest.raises(
        HsrValidationError,
        match="below configured range",
    ):
        validate_hsr_grid(
            grid,
            expected_nx=1,
            expected_ny=1,
        )


def test_rejects_implausibly_large_value() -> None:
    grid = make_grid(
        np.array([[10_001]], dtype=np.int16)
    )

    with pytest.raises(
        HsrValidationError,
        match="above configured range",
    ):
        validate_hsr_grid(
            grid,
            expected_nx=1,
            expected_ny=1,
        )
