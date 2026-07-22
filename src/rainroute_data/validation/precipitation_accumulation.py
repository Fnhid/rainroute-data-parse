from __future__ import annotations

from collections.abc import Sequence


def trapezoidal_accumulation_mm(
    rain_rates_mm_h: Sequence[float],
    *,
    interval_minutes: int,
) -> float:
    """Integrate equally spaced rain rates into accumulated rainfall."""
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be positive")

    if len(rain_rates_mm_h) < 2:
        raise ValueError("At least two rain-rate samples are required")

    interval_hours = interval_minutes / 60.0

    return sum(
        (left + right) * 0.5 * interval_hours
        for left, right in zip(
            rain_rates_mm_h[:-1],
            rain_rates_mm_h[1:],
            strict=True,
        )
    )
