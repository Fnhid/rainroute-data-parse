from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rainroute_data.parsers.aws_stations import decode_kma_text


class HspAwsPointParseError(ValueError):
    """Raised when HSP AWS-point data cannot be parsed."""


@dataclass(frozen=True)
class HspAwsPoint:
    observed_at: datetime
    station_id: int
    product: str
    quality_code: str
    echo_mm_h: float | None
    status: str
    echo_height_m: float | None
    station_name: str


def _parse_echo(value: str) -> tuple[float | None, str]:
    parsed = float(value)

    if parsed == -250.0:
        return None, "no_rain"

    if parsed == -300.0:
        return None, "outside_observation"

    if parsed < 0:
        return None, f"unknown_sentinel:{parsed}"

    return parsed, "physical"


def _optional_float(value: str) -> float | None:
    parsed = float(value)

    if parsed <= -250.0:
        return None

    return parsed


def parse_hsp_aws_points_text(
    text: str,
) -> list[HspAwsPoint]:
    points: list[HspAwsPoint] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        fields = [field.strip() for field in stripped.split(",")]

        while fields and fields[-1] in {"", "="}:
            fields.pop()

        if len(fields) < 7:
            raise HspAwsPointParseError(
                f"Expected 7 columns at line {line_number}, "
                f"received {len(fields)}: {line}"
            )

        try:
            echo_mm_h, status = _parse_echo(fields[4])

            points.append(
                HspAwsPoint(
                    observed_at=datetime.strptime(
                        fields[0],
                        "%Y%m%d%H%M",
                    ),
                    station_id=int(fields[1]),
                    product=fields[2],
                    quality_code=fields[3],
                    echo_mm_h=echo_mm_h,
                    status=status,
                    echo_height_m=_optional_float(fields[5]),
                    station_name=fields[6],
                )
            )
        except ValueError as exc:
            raise HspAwsPointParseError(
                f"Invalid row at line {line_number}: {line}"
            ) from exc

    if not points:
        raise HspAwsPointParseError(
            "No HSP AWS-point observations were parsed"
        )

    return points


def parse_hsp_aws_points_file(
    path: Path,
) -> list[HspAwsPoint]:
    return parse_hsp_aws_points_text(
        decode_kma_text(path.read_bytes())
    )
