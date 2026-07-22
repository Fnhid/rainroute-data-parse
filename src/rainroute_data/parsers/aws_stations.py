from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class AwsStationParseError(ValueError):
    """Raised when AWS station metadata cannot be parsed."""


@dataclass(frozen=True)
class AwsStation:
    station_id: int
    longitude: float
    latitude: float


def decode_kma_text(payload: bytes) -> str:
    for encoding in ("cp949", "euc-kr", "utf-8"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue

    return payload.decode("cp949", errors="replace")


def parse_aws_stations_text(text: str) -> dict[int, AwsStation]:
    stations: dict[int, AwsStation] = {}

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        fields = stripped.split()

        if len(fields) < 3:
            continue

        try:
            station_id = int(fields[0])
            longitude = float(fields[1])
            latitude = float(fields[2])
        except ValueError as exc:
            raise AwsStationParseError(
                f"Invalid AWS station row at line {line_number}: {line}"
            ) from exc

        stations[station_id] = AwsStation(
            station_id=station_id,
            longitude=longitude,
            latitude=latitude,
        )

    if not stations:
        raise AwsStationParseError("No AWS stations were parsed")

    return stations


def parse_aws_stations_file(path: Path) -> dict[int, AwsStation]:
    text = decode_kma_text(path.read_bytes())
    return parse_aws_stations_text(text)
