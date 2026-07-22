from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from rainroute_data.parsers.radar_hsp import (
    HSP_MINIMUM_DISPLAY,
    HSP_NO_OBSERVATION,
    HSP_OUTSIDE_OBSERVATION,
    HspGrid,
    hsp_raw_to_rain_rate,
)


class HspValidationError(ValueError):
    """Raised when an HSP grid fails structural or range validation."""


@dataclass(frozen=True)
class HspValidationReport:
    shape: tuple[int, int]
    total_cells: int
    physical_cells: int
    minimum_display_cells: int
    no_observation_cells: int
    outside_cells: int
    raw_minimum: int | None
    raw_maximum: int | None
    rain_rate_minimum_mm_h: float | None
    rain_rate_maximum_mm_h: float | None
    declared_block_count: int
    actual_block_count: int

    @property
    def physical_fraction(self) -> float:
        return self.physical_cells / self.total_cells


def validate_hsp_grid(
    grid: HspGrid,
    *,
    expected_nx: int = 2305,
    expected_ny: int = 2881,
    provisional_scale: float = 0.01,
    maximum_rain_rate_mm_h: float = 500.0,
) -> HspValidationReport:
    if grid.header.nx != expected_nx:
        raise HspValidationError(
            f"Unexpected HSP nx: {grid.header.nx}"
        )

    if grid.header.ny != expected_ny:
        raise HspValidationError(
            f"Unexpected HSP ny: {grid.header.ny}"
        )

    if grid.shape != (expected_ny, expected_nx):
        raise HspValidationError(
            f"Unexpected HSP shape: {grid.shape}"
        )

    if grid.primary_data_name != "rainfall":
        raise HspValidationError(
            f"Primary HSP block is not rainfall: {grid.primary_data_name}"
        )

    values = grid.values

    minimum_display = values == HSP_MINIMUM_DISPLAY
    no_observation = values == HSP_NO_OBSERVATION
    outside = values == HSP_OUTSIDE_OBSERVATION

    special = minimum_display | no_observation | outside
    physical = ~special
    physical_values = values[physical]

    if np.any(physical_values < 0):
        unexpected = np.unique(
            physical_values[physical_values < 0]
        )[:20]
        raise HspValidationError(
            f"Unexpected negative physical HSP values: {unexpected.tolist()}"
        )

    rain_rate = hsp_raw_to_rain_rate(
        values,
        scale=provisional_scale,
    )
    finite_rain_rate = rain_rate[np.isfinite(rain_rate)]

    if finite_rain_rate.size:
        maximum = float(finite_rain_rate.max())

        if maximum > maximum_rain_rate_mm_h:
            raise HspValidationError(
                "HSP rain rate exceeds configured maximum: "
                f"{maximum:.3f} mm/h"
            )

        rain_rate_minimum = float(finite_rain_rate.min())
        rain_rate_maximum = maximum
    else:
        rain_rate_minimum = None
        rain_rate_maximum = None

    return HspValidationReport(
        shape=grid.shape,
        total_cells=int(values.size),
        physical_cells=int(physical.sum()),
        minimum_display_cells=int(minimum_display.sum()),
        no_observation_cells=int(no_observation.sum()),
        outside_cells=int(outside.sum()),
        raw_minimum=(
            int(physical_values.min())
            if physical_values.size
            else None
        ),
        raw_maximum=(
            int(physical_values.max())
            if physical_values.size
            else None
        ),
        rain_rate_minimum_mm_h=rain_rate_minimum,
        rain_rate_maximum_mm_h=rain_rate_maximum,
        declared_block_count=grid.header.declared_block_count,
        actual_block_count=grid.actual_block_count,
    )
