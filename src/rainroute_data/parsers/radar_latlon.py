from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt


class RadarLatLonParseError(ValueError):
    """Raised when a radar latitude/longitude payload is malformed."""


ByteOrder = Literal["little", "big"]


@dataclass(frozen=True)
class RadarCoordinateGrid:
    nx: int
    ny: int
    values: npt.NDArray[np.float32]
    byte_order: ByteOrder

    @property
    def shape(self) -> tuple[int, int]:
        return self.values.shape


def _integer_dtype(byte_order: ByteOrder) -> np.dtype[np.int16]:
    return np.dtype("<i2" if byte_order == "little" else ">i2")


def _float_dtype(byte_order: ByteOrder) -> np.dtype[np.float32]:
    return np.dtype("<f4" if byte_order == "little" else ">f4")


def _decode_dimensions(
    payload: bytes,
    *,
    byte_order: ByteOrder,
) -> tuple[int, int]:
    """Decode the coordinate-file header.

    Unlike the HSR value binary, the observed latitude/longitude endpoint
    stores dimensions as (ny, nx).
    """
    if len(payload) < 4:
        raise RadarLatLonParseError(
            f"Radar coordinate payload is too short: {len(payload)} bytes"
        )

    header = np.frombuffer(
        payload,
        dtype=_integer_dtype(byte_order),
        count=2,
    )

    ny = int(header[0])
    nx = int(header[1])

    return nx, ny


def _expected_size(nx: int, ny: int) -> int:
    return 4 + nx * ny * np.dtype(np.float32).itemsize


def _dimensions_are_plausible(nx: int, ny: int) -> bool:
    return 1 <= nx <= 20_000 and 1 <= ny <= 20_000


def detect_latlon_byte_order(payload: bytes) -> ByteOrder:
    candidates: list[ByteOrder] = []

    for byte_order in ("little", "big"):
        nx, ny = _decode_dimensions(
            payload,
            byte_order=byte_order,
        )

        if not _dimensions_are_plausible(nx, ny):
            continue

        if _expected_size(nx, ny) == len(payload):
            candidates.append(byte_order)

    if len(candidates) == 1:
        return candidates[0]

    if not candidates:
        details = []

        for byte_order in ("little", "big"):
            nx, ny = _decode_dimensions(
                payload,
                byte_order=byte_order,
            )
            details.append(
                f"{byte_order}: nx={nx}, ny={ny}, "
                f"expected={_expected_size(nx, ny)}"
            )

        raise RadarLatLonParseError(
            "Could not determine radar coordinate byte order. "
            f"payload_size={len(payload)}; "
            + "; ".join(details)
        )

    raise RadarLatLonParseError(
        "Radar coordinate byte order is ambiguous"
    )


def parse_radar_latlon_binary(
    payload: bytes,
) -> RadarCoordinateGrid:
    byte_order = detect_latlon_byte_order(payload)

    nx, ny = _decode_dimensions(
        payload,
        byte_order=byte_order,
    )

    flat = np.frombuffer(
        payload,
        dtype=_float_dtype(byte_order),
        offset=4,
        count=nx * ny,
    )

    values = flat.reshape(ny, nx).astype(
        np.float32,
        copy=True,
    )

    return RadarCoordinateGrid(
        nx=nx,
        ny=ny,
        values=values,
        byte_order=byte_order,
    )


def parse_radar_latlon_file(
    path: Path,
) -> RadarCoordinateGrid:
    return parse_radar_latlon_binary(path.read_bytes())
