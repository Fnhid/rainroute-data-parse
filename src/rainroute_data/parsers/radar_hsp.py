from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import numpy.typing as npt

from rainroute_data.parsers.compression import decompress_payload


class HspParseError(ValueError):
    """Raised when an HSP composite payload is malformed."""


HSP_HEADER_SIZE = 1024
HSP_HEAD_SIZE = 64
HSP_STATION_ENTRY_SIZE = 20
HSP_MAX_STATIONS = 48

GRID_DTYPE = np.dtype("<i2")

DATA_CODE_NAMES = {
    1: "echo",
    2: "height",
    3: "station_order",
    4: "data_count",
    5: "rainfall",
    6: "hydrometeor",
    15: "echo_count_below_3km",
}

PRODUCT_TYPE_NAMES = {
    0: "PPI",
    1: "CAPPI",
    2: "CMAX",
    3: "ETOP",
    4: "EBASE",
    5: "HSR",
    6: "HCI",
    7: "VIL",
    8: "WIND",
    9: "LNG",
    10: "PCP",
    15: "NUM",
}

HSP_MINIMUM_DISPLAY = -20_000
HSP_NO_OBSERVATION = -25_000
HSP_OUTSIDE_OBSERVATION = -30_000


@dataclass(frozen=True)
class RadarTime:
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int

    def as_datetime(self) -> datetime:
        return datetime(
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )


@dataclass(frozen=True)
class HspHeader:
    version: int
    product_type: int
    observation_time: RadarTime
    generation_time: RadarTime
    station_count: int
    map_code: int
    map_etc: int
    nx: int
    ny: int
    nz: int
    horizontal_spacing_m: int
    vertical_spacing_m: int
    minimum_height_m: int
    declared_block_count: int
    data_codes: tuple[int, ...]

    @property
    def product_type_name(self) -> str:
        return PRODUCT_TYPE_NAMES.get(
            self.product_type,
            f"unknown:{self.product_type}",
        )

    @property
    def data_code_names(self) -> tuple[str, ...]:
        return tuple(
            DATA_CODE_NAMES.get(code, f"unknown:{code}")
            for code in self.data_codes
        )


@dataclass(frozen=True)
class HspGrid:
    header: HspHeader
    raw_header: bytes
    values: npt.NDArray[np.int16]
    actual_block_count: int
    compression: str
    compressed_size: int
    decompressed_size: int

    @property
    def shape(self) -> tuple[int, int]:
        return self.values.shape

    @property
    def nx(self) -> int:
        return self.header.nx

    @property
    def ny(self) -> int:
        return self.header.ny

    @property
    def primary_data_code(self) -> int | None:
        if not self.header.data_codes:
            return None

        return self.header.data_codes[0]

    @property
    def primary_data_name(self) -> str | None:
        code = self.primary_data_code

        if code is None:
            return None

        return DATA_CODE_NAMES.get(code, f"unknown:{code}")


def _parse_time(payload: bytes, offset: int) -> RadarTime:
    year = struct.unpack_from("<h", payload, offset)[0]

    return RadarTime(
        year=year,
        month=payload[offset + 2],
        day=payload[offset + 3],
        hour=payload[offset + 4],
        minute=payload[offset + 5],
        second=payload[offset + 6],
    )


def parse_hsp_header(payload: bytes) -> HspHeader:
    if len(payload) < HSP_HEAD_SIZE:
        raise HspParseError(
            f"HSP header is too short: {len(payload)} bytes"
        )

    observation_time = _parse_time(payload, 3)
    generation_time = _parse_time(payload, 10)

    declared_block_count = payload[32]
    all_data_codes = tuple(payload[33:49])

    data_codes = tuple(
        code
        for code in all_data_codes[:declared_block_count]
        if code != 0
    )

    return HspHeader(
        version=payload[0],
        product_type=struct.unpack_from("<h", payload, 1)[0],
        observation_time=observation_time,
        generation_time=generation_time,
        station_count=payload[17],
        map_code=payload[18],
        map_etc=payload[19],
        nx=struct.unpack_from("<h", payload, 20)[0],
        ny=struct.unpack_from("<h", payload, 22)[0],
        nz=struct.unpack_from("<h", payload, 24)[0],
        horizontal_spacing_m=struct.unpack_from(
            "<h",
            payload,
            26,
        )[0],
        vertical_spacing_m=struct.unpack_from(
            "<h",
            payload,
            28,
        )[0],
        minimum_height_m=struct.unpack_from(
            "<h",
            payload,
            30,
        )[0],
        declared_block_count=declared_block_count,
        data_codes=data_codes,
    )


def parse_hsp_payload(payload: bytes) -> HspGrid:
    decompressed = decompress_payload(payload)
    content = decompressed.content

    if len(content) < HSP_HEADER_SIZE:
        raise HspParseError(
            "Decompressed HSP payload is smaller than its header: "
            f"{len(content)} bytes"
        )

    header = parse_hsp_header(content[:HSP_HEAD_SIZE])

    if header.nx <= 0 or header.ny <= 0:
        raise HspParseError(
            f"Invalid HSP dimensions: nx={header.nx}, ny={header.ny}"
        )

    block_size = header.nx * header.ny * GRID_DTYPE.itemsize
    body_size = len(content) - HSP_HEADER_SIZE

    if body_size <= 0 or body_size % block_size != 0:
        raise HspParseError(
            "HSP body is not an integral number of grid blocks: "
            f"body_size={body_size}, block_size={block_size}"
        )

    actual_block_count = body_size // block_size

    # Current rdr_cmp_file.php HSP payload has been observed to contain one
    # physical block even though the inherited header declares three.
    first_block = np.frombuffer(
        content,
        dtype=GRID_DTYPE,
        offset=HSP_HEADER_SIZE,
        count=header.nx * header.ny,
    )

    values = first_block.reshape(
        header.ny,
        header.nx,
    ).astype(np.int16, copy=True)

    return HspGrid(
        header=header,
        raw_header=content[:HSP_HEADER_SIZE],
        values=values,
        actual_block_count=actual_block_count,
        compression=decompressed.compression,
        compressed_size=decompressed.compressed_size,
        decompressed_size=decompressed.decompressed_size,
    )


def parse_hsp_file(path: Path) -> HspGrid:
    return parse_hsp_payload(path.read_bytes())


def hsp_raw_to_rain_rate(
    values: npt.NDArray[np.int16],
    *,
    scale: float = 0.01,
) -> npt.NDArray[np.float32]:
    """Convert HSP raw rainfall values to provisional rain rate in mm/h.

    The default scale of 0.01 is currently inferred from the observed value
    distribution and must be verified against AWS or another authoritative
    rainfall product before being treated as final.
    """
    result = values.astype(np.float32) * scale

    special = np.isin(
        values,
        (
            HSP_MINIMUM_DISPLAY,
            HSP_NO_OBSERVATION,
            HSP_OUTSIDE_OBSERVATION,
        ),
    )
    result[special] = np.nan

    return result
