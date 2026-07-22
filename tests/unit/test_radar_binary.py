import numpy as np
import pytest

from rainroute_data.parsers.radar_binary import (
    RadarBinaryParseError,
    hsr_to_dbz,
    no_echo_mask,
    outside_observation_mask,
    parse_radar_binary,
    valid_echo_mask,
)


def make_payload(
    values: np.ndarray,
    *,
    byte_order: str,
) -> bytes:
    ny, nx = values.shape
    dtype = np.dtype("<i2" if byte_order == "little" else ">i2")

    header = np.array(
        [nx, ny],
        dtype=dtype,
    ).tobytes()

    body = values.astype(
        dtype,
        copy=False,
    ).tobytes()

    return header + body


@pytest.mark.parametrize(
    "byte_order",
    ["little", "big"],
)
def test_parse_radar_binary(byte_order: str) -> None:
    values = np.array(
        [
            [100, 200, 300],
            [-25_000, -30_000, 450],
        ],
        dtype=np.int16,
    )

    grid = parse_radar_binary(
        make_payload(
            values,
            byte_order=byte_order,
        )
    )

    assert grid.nx == 3
    assert grid.ny == 2
    assert grid.shape == (2, 3)
    assert grid.byte_order == byte_order
    np.testing.assert_array_equal(
        grid.values,
        values,
    )


def test_rejects_truncated_payload() -> None:
    values = np.array(
        [[100, 200]],
        dtype=np.int16,
    )
    payload = make_payload(
        values,
        byte_order="little",
    )

    with pytest.raises(RadarBinaryParseError):
        parse_radar_binary(payload[:-1])


def test_hsr_value_conversion_and_masks() -> None:
    values = np.array(
        [
            [1234, -25_000],
            [-30_000, 500],
        ],
        dtype=np.int16,
    )

    dbz = hsr_to_dbz(values)

    assert dbz[0, 0] == pytest.approx(12.34)
    assert dbz[1, 1] == pytest.approx(5.0)
    assert np.isnan(dbz[0, 1])
    assert np.isnan(dbz[1, 0])

    np.testing.assert_array_equal(
        valid_echo_mask(values),
        [
            [True, False],
            [False, True],
        ],
    )

    np.testing.assert_array_equal(
        no_echo_mask(values),
        [
            [False, True],
            [False, False],
        ],
    )

    np.testing.assert_array_equal(
        outside_observation_mask(values),
        [
            [False, False],
            [True, False],
        ],
    )
