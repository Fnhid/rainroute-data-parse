from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class RainEvent:
    start_time: datetime
    end_time: datetime
    wet_target_count: int
    wet_station_observation_count: int
    maximum_aws_accumulation_15m_mm: float
    maximum_hsp_accumulation_15m_mm: float


def detect_rain_events_from_calibration(
    calibration_file: Path,
    *,
    wet_threshold_mm: float = 0.1,
    padding_minutes: int = 30,
    merge_gap_minutes: int = 30,
) -> list[RainEvent]:
    if wet_threshold_mm < 0:
        raise ValueError("wet_threshold_mm must be non-negative")

    if padding_minutes < 0:
        raise ValueError("padding_minutes must be non-negative")

    if merge_gap_minutes < 0:
        raise ValueError("merge_gap_minutes must be non-negative")

    data = pd.read_csv(calibration_file)

    required_columns = {
        "target_time_kst",
        "aws_accumulation_15m_mm",
        "hsp_accumulation_15m_mm",
    }

    missing = required_columns - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing calibration columns: {sorted(missing)}"
        )

    data["target_time"] = pd.to_datetime(
        data["target_time_kst"],
        utc=True,
    )

    data["wet"] = (
        data["aws_accumulation_15m_mm"]
        >= wet_threshold_mm
    )

    grouped = (
        data.groupby("target_time", as_index=False)
        .agg(
            wet_station_observation_count=(
                "wet",
                "sum",
            ),
            maximum_aws_accumulation_15m_mm=(
                "aws_accumulation_15m_mm",
                "max",
            ),
            maximum_hsp_accumulation_15m_mm=(
                "hsp_accumulation_15m_mm",
                "max",
            ),
        )
        .sort_values("target_time")
    )

    wet_times = grouped.loc[
        grouped["wet_station_observation_count"] > 0
    ]

    if wet_times.empty:
        return []

    padding = timedelta(minutes=padding_minutes)
    merge_gap = timedelta(minutes=merge_gap_minutes)

    raw_events: list[dict[str, object]] = []

    for row in wet_times.itertuples(index=False):
        target_time = row.target_time.to_pydatetime()

        candidate_start = target_time - padding
        candidate_end = target_time + padding

        if (
            not raw_events
            or candidate_start
            > raw_events[-1]["end_time"] + merge_gap
        ):
            raw_events.append(
                {
                    "start_time": candidate_start,
                    "end_time": candidate_end,
                    "wet_target_count": 1,
                    "wet_station_observation_count": int(
                        row.wet_station_observation_count
                    ),
                    "maximum_aws_accumulation_15m_mm": float(
                        row.maximum_aws_accumulation_15m_mm
                    ),
                    "maximum_hsp_accumulation_15m_mm": float(
                        row.maximum_hsp_accumulation_15m_mm
                    ),
                }
            )
            continue

        current = raw_events[-1]
        current["end_time"] = max(
            current["end_time"],
            candidate_end,
        )
        current["wet_target_count"] += 1
        current["wet_station_observation_count"] += int(
            row.wet_station_observation_count
        )
        current["maximum_aws_accumulation_15m_mm"] = max(
            current[
                "maximum_aws_accumulation_15m_mm"
            ],
            float(
                row.maximum_aws_accumulation_15m_mm
            ),
        )
        current["maximum_hsp_accumulation_15m_mm"] = max(
            current[
                "maximum_hsp_accumulation_15m_mm"
            ],
            float(
                row.maximum_hsp_accumulation_15m_mm
            ),
        )

    return [
        RainEvent(
            start_time=event["start_time"],
            end_time=event["end_time"],
            wet_target_count=event[
                "wet_target_count"
            ],
            wet_station_observation_count=event[
                "wet_station_observation_count"
            ],
            maximum_aws_accumulation_15m_mm=event[
                "maximum_aws_accumulation_15m_mm"
            ],
            maximum_hsp_accumulation_15m_mm=event[
                "maximum_hsp_accumulation_15m_mm"
            ],
        )
        for event in raw_events
    ]
