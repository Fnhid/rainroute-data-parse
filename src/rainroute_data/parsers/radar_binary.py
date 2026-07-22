from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt


class RadarBinaryParseError(ValueError):
    """Raised when a radar binary payload does not match the documented format."""


ByteOrder = Literal["little", "big"]


@dataclass(frozen=True)
class RadarGrid:
    nx: int
    ny: int
    values: npt.NDArray[np.int16]
    byte_order: ByteOrder

    @property
    def shape(self) -> tuple[int, int]:
        return self.values.shape


def _decode_dimensions(
    payload: bytes,
    *,
    byte_order: ByteOrder,
) -> tuple[int, int]:
    if len(payload) < 4:
        raise RadarBinaryParseError(
            f"Radar payload is too short: {len(payload)} bytes"
        )

    dtype = np.dtype("<i2" if byte_order == "little" else ">i2")
    header = np.frombuffer(payload[:4], dtype=dtype, count=2)

    return int(header[0]), int(header[1])


def _expected_size(nx: int, ny: int) -> int:
    return 4 + nx * ny * np.dtype(np.int16).itemsize


def _dimensions_are_plausible(nx: int, ny: int) -> bool:
    return 1 <= nx <= 20_000 and 1 <= ny <= 20_000


def detect_byte_order(payload: bytes) -> ByteOrder:
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

        raise RadarBinaryParseError(
            "Could not determine radar binary byte order. "
            f"payload_size={len(payload)}; "
            + "; ".join(details)
        )

    raise RadarBinaryParseError(
        "Radar binary byte order is ambiguous"
    )


def parse_radar_binary(payload: bytes) -> RadarGrid:
    byte_order = detect_byte_order(payload)
    nx, ny = _decode_dimensions(
        payload,
        byte_order=byte_order,
    )

    dtype = np.dtype("<i2" if byte_order == "little" else ">i2")
    flat = np.frombuffer(
        payload,
        dtype=dtype,
        offset=4,
        count=nx * ny,
    )

    # 문서상 자료는 좌하단에서 우상단 방향으로 수평 우선 저장된다.
    # 배열 축은 [y, x]로 둔다.
    values = flat.reshape(ny, nx).astype(
        np.int16,
        copy=True,
    )

    return RadarGrid(
        nx=nx,
        ny=ny,
        values=values,
        byte_order=byte_order,
    )


def parse_radar_binary_file(path: Path) -> RadarGrid:
    return parse_radar_binary(path.read_bytes())


def hsr_to_dbz(
    values: npt.NDArray[np.int16],
) -> npt.NDArray[np.float32]:
    """Convert HSR integer encoding dBZ*100 into dBZ.

    Special values remain NaN:
    - -25000: inside radar range, no echo
    - -30000: outside radar observation range
    """
    result = values.astype(np.float32) / 100.0

    invalid = (values == -25_000) | (values == -30_000)
    result[invalid] = np.nan

    return result


def valid_echo_mask(
    values: npt.NDArray[np.int16],
) -> npt.NDArray[np.bool_]:
    return (values != -25_000) & (values != -30_000)


def no_echo_mask(
    values: npt.NDArray[np.int16],
) -> npt.NDArray[np.bool_]:
    return values == -25_000


def outside_observation_mask(
    values: npt.NDArray[np.int16],
) -> npt.NDArray[np.bool_]:
    return values == -30_000
