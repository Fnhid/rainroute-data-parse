import numpy as np
import pytest

from rainroute_data.parsers.radar_latlon import (
    RadarLatLonParseError,
    parse_radar_latlon_binary,
)


def make_payload(
    values: np.ndarray,
    *,
    byte_order: str,
) -> bytes:
    ny, nx = values.shape

    integer_dtype = np.dtype(
        "<i2" if byte_order == "little" else ">i2"
    )
    float_dtype = np.dtype(
        "<f4" if byte_order == "little" else ">f4"
    )

    header = np.array(
        [ny, nx],
        dtype=integer_dtype,
    ).tobytes()

    body = values.astype(
        float_dtype,
        copy=False,
    ).tobytes()

    return header + body


@pytest.mark.parametrize(
    "byte_order",
    ["little", "big"],
)
def test_parse_radar_latlon_binary(
    byte_order: str,
) -> None:
    values = np.array(
        [
            [126.0, 126.5, 127.0],
            [126.1, 126.6, 127.1],
        ],
        dtype=np.float32,
    )

    grid = parse_radar_latlon_binary(
        make_payload(
            values,
            byte_order=byte_order,
        )
    )

    assert grid.nx == 3
    assert grid.ny == 2
    assert grid.shape == (2, 3)
    assert grid.byte_order == byte_order

    np.testing.assert_allclose(
        grid.values,
        values,
    )


def test_rejects_truncated_payload() -> None:
    values = np.array(
        [[126.0, 127.0]],
        dtype=np.float32,
    )

    payload = make_payload(
        values,
        byte_order="little",
    )

    with pytest.raises(RadarLatLonParseError):
        parse_radar_latlon_binary(payload[:-1])
