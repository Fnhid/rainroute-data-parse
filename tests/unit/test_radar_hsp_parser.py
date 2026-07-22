import gzip

import numpy as np
import pytest

from rainroute_data.parsers.radar_hsp import (
    HspParseError,
    parse_hsp_payload,
)


def make_payload(
    values: np.ndarray,
    *,
    product_type: int = 5,
    data_code: int = 5,
) -> bytes:
    ny, nx = values.shape

    header = bytearray(1024)

    header[0] = 1
    header[1:3] = product_type.to_bytes(
        2,
        byteorder="little",
        signed=True,
    )

    header[3:5] = (2026).to_bytes(
        2,
        byteorder="little",
        signed=True,
    )
    header[5] = 7
    header[6] = 22
    header[7] = 19
    header[8] = 10
    header[9] = 0

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
    header[33] = data_code

    body = values.astype(
        "<i2",
        copy=False,
    ).tobytes()

    return gzip.compress(
        bytes(header) + body,
        mtime=0,
    )


def test_parse_hsp_payload() -> None:
    values = np.array(
        [
            [2, 100, -25_000],
            [13_407, -30_000, -20_000],
        ],
        dtype=np.int16,
    )

    grid = parse_hsp_payload(
        make_payload(values)
    )

    assert grid.shape == (2, 3)
    assert grid.header.version == 1
    assert grid.header.product_type == 5
    assert grid.header.product_type_name == "HSR"
    assert grid.header.nx == 3
    assert grid.header.ny == 2
    assert grid.header.horizontal_spacing_m == 500
    assert grid.header.data_codes == (5,)
    assert grid.header.data_code_names == ("rainfall",)
    assert grid.primary_data_name == "rainfall"
    assert grid.actual_block_count == 1

    np.testing.assert_array_equal(
        grid.values,
        values,
    )


def test_rejects_non_integral_grid_body() -> None:
    payload = gzip.compress(
        bytes(1024) + b"\x00",
        mtime=0,
    )

    with pytest.raises(HspParseError):
        parse_hsp_payload(payload)
