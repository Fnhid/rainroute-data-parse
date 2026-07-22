from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rainroute_data.parsers.aws_stations import decode_kma_text


class AwsMinuteParseError(ValueError):
    """Raised when AWS minute observations cannot be parsed."""


@dataclass(frozen=True)
class AwsMinuteObservation:
    observed_at: datetime
    station_id: int
    rain_15m_mm: float | None
    rain_60m_mm: float | None
    rain_12h_mm: float | None
    rain_day_mm: float | None


def _optional_measurement(value: str) -> float | None:
    parsed = float(value)

    if parsed <= -50.0:
        return None

    return parsed


def parse_aws_minute_text(
    text: str,
) -> list[AwsMinuteObservation]:
    observations: list[AwsMinuteObservation] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        fields = [field.strip() for field in stripped.split(",")]

        if fields and fields[-1] == "=":
            fields.pop()

        # Columns documented in the returned help header:
        # time, stn, WD1, WS1, WDS, WSS, WD10, WS10, TA, RE,
        # RN-15m, RN-60m, RN-12H, RN-DAY, HM, PA, PS, TD
        if len(fields) < 18:
            raise AwsMinuteParseError(
                f"Expected at least 18 columns at line {line_number}, "
                f"received {len(fields)}"
            )

        try:
            observed_at = datetime.strptime(
                fields[0],
                "%Y%m%d%H%M",
            )
            station_id = int(fields[1])

            observation = AwsMinuteObservation(
                observed_at=observed_at,
                station_id=station_id,
                rain_15m_mm=_optional_measurement(fields[10]),
                rain_60m_mm=_optional_measurement(fields[11]),
                rain_12h_mm=_optional_measurement(fields[12]),
                rain_day_mm=_optional_measurement(fields[13]),
            )
        except ValueError as exc:
            raise AwsMinuteParseError(
                f"Invalid AWS minute row at line {line_number}: {line}"
            ) from exc

        observations.append(observation)

    if not observations:
        raise AwsMinuteParseError("No AWS minute observations were parsed")

    return observations


def parse_aws_minute_file(
    path: Path,
) -> list[AwsMinuteObservation]:
    text = decode_kma_text(path.read_bytes())
    return parse_aws_minute_text(text)
