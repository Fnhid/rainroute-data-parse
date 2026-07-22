from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from pathlib import Path

from rainroute_data.datasets.rain_events import (
    detect_rain_events_from_calibration,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--calibration-file",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--wet-threshold-mm",
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "--padding-minutes",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--merge-gap-minutes",
        type=int,
        default=30,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    events = detect_rain_events_from_calibration(
        args.calibration_file,
        wet_threshold_mm=args.wet_threshold_mm,
        padding_minutes=args.padding_minutes,
        merge_gap_minutes=args.merge_gap_minutes,
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "event_id",
        "start_time",
        "end_time",
        "duration_minutes",
        "wet_target_count",
        "wet_station_observation_count",
        "maximum_aws_accumulation_15m_mm",
        "maximum_hsp_accumulation_15m_mm",
    ]

    temporary = args.output.with_suffix(
        args.output.suffix + ".tmp"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for index, event in enumerate(
            events,
            start=1,
        ):
            values = asdict(event)
            start_time = event.start_time
            end_time = event.end_time

            writer.writerow(
                {
                    "event_id": (
                        f"{start_time:%Y%m%dT%H%M%S}"
                        f"_{index:03d}"
                    ),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_minutes": int(
                        (
                            end_time - start_time
                        ).total_seconds()
                        / 60
                    ),
                    "wet_target_count": values[
                        "wet_target_count"
                    ],
                    "wet_station_observation_count": values[
                        "wet_station_observation_count"
                    ],
                    "maximum_aws_accumulation_15m_mm": values[
                        "maximum_aws_accumulation_15m_mm"
                    ],
                    "maximum_hsp_accumulation_15m_mm": values[
                        "maximum_hsp_accumulation_15m_mm"
                    ],
                }
            )

    temporary.replace(args.output)

    print(f"event_count={len(events)}")

    for index, event in enumerate(
        events,
        start=1,
    ):
        duration_minutes = int(
            (
                event.end_time
                - event.start_time
            ).total_seconds()
            / 60
        )

        print(
            f"event={index:03d} "
            f"start={event.start_time.isoformat()} "
            f"end={event.end_time.isoformat()} "
            f"duration_minutes={duration_minutes} "
            f"wet_targets={event.wet_target_count} "
            f"max_aws_15m_mm="
            f"{event.maximum_aws_accumulation_15m_mm:.3f}"
        )

    print(f"output={args.output}")


if __name__ == "__main__":
    main()
