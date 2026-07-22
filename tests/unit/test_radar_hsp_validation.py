import gzip

import numpy as np
import pytest

from rainroute_data.parsers.radar_hsp import parse_hsp_payload
from rainroute_data.validation.radar_hsp import (
    HspValidationError,
    validate_hsp_grid,
)


def make_payload(values: np.ndarray) -> bytes:
    ny, nx = values.shape

    header = bytearray(1024)

    header[0] = 1
    header[1:3] = (5).to_bytes(
        2,
        byteorder="little",
        signed=True,
    )

    header[20:22] = nx.to_bytes(
        2,
        byteorder="little",
        signed=True,
    )
    header[22:24] = ny.to_bytes(
        2,
        byteorder="little",
        signed=True,
    )
    header[24:26] = (1).to_bytes(
        2,
        byteorder="little",
        signed=True,
    )
    header[26:28] = (500).to_bytes(
        2,
        byteorder="little",
        signed=True,
    )

    header[32] = 1
    header[33] = 5

    content = (
        bytes(header)
        + values.astype("<i2", copy=False).tobytes()
    )

    return gzip.compress(content, mtime=0)


def test_validate_hsp_grid() -> None:
    values = np.array(
        [
            [2, 100, -25_000],
            [13_407, -30_000, -20_000],
        ],
        dtype=np.int16,
    )

    grid = parse_hsp_payload(make_payload(values))

    report = validate_hsp_grid(
        grid,
        expected_nx=3,
        expected_ny=2,
    )

    assert report.physical_cells == 3
    assert report.raw_minimum == 2
    assert report.raw_maximum == 13_407
    assert report.rain_rate_minimum_mm_h == pytest.approx(0.02)
    assert report.rain_rate_maximum_mm_h == pytest.approx(134.07)
    assert report.no_observation_cells == 1
    assert report.outside_cells == 1
    assert report.minimum_display_cells == 1


def test_rejects_negative_physical_value() -> None:
    values = np.array(
        [[-1]],
        dtype=np.int16,
    )

    grid = parse_hsp_payload(make_payload(values))

    with pytest.raises(
        HspValidationError,
        match="Unexpected negative physical",
    ):
        validate_hsp_grid(
            grid,
            expected_nx=1,
            expected_ny=1,
        )


def test_rejects_implausible_rain_rate() -> None:
    values = np.array(
        [[30_000]],
        dtype=np.int16,
    )

    grid = parse_hsp_payload(make_payload(values))

    with pytest.raises(
        HspValidationError,
        match="exceeds configured maximum",
    ):
        validate_hsp_grid(
            grid,
            expected_nx=1,
            expected_ny=1,
            maximum_rain_rate_mm_h=200.0,
        )
