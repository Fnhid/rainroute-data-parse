from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from rainroute_data.parsers.radar_binary import (
    HSR_NO_ECHO,
    HSR_OUTSIDE_OBSERVATION,
    HSR_UNDOCUMENTED_MASK,
    RadarGrid,
)


class HsrValidationError(ValueError):
    """Raised when an HSR grid fails structural validation."""


@dataclass(frozen=True)
class HsrValidationReport:
    nx: int
    ny: int
    total_cells: int
    no_echo_cells: int
    outside_cells: int
    undocumented_mask_cells: int
    physical_cells: int
    negative_physical_cells: int
    minimum_physical_raw: int | None
    maximum_physical_raw: int | None

    @property
    def physical_fraction(self) -> float:
        return self.physical_cells / self.total_cells

    @property
    def undocumented_mask_fraction(self) -> float:
        return self.undocumented_mask_cells / self.total_cells


def validate_hsr_grid(
    grid: RadarGrid,
    *,
    expected_nx: int | None = 2305,
    expected_ny: int | None = 2881,
    minimum_physical_raw: int = -10_000,
    maximum_physical_raw: int = 10_000,
) -> HsrValidationReport:
    if expected_nx is not None and grid.nx != expected_nx:
        raise HsrValidationError(
            f"Unexpected HSR nx: expected={expected_nx}, actual={grid.nx}"
        )

    if expected_ny is not None and grid.ny != expected_ny:
        raise HsrValidationError(
            f"Unexpected HSR ny: expected={expected_ny}, actual={grid.ny}"
        )

    values = grid.values
    expected_shape = (grid.ny, grid.nx)

    if values.shape != expected_shape:
        raise HsrValidationError(
            f"Grid shape mismatch: shape={values.shape}, "
            f"header={expected_shape}"
        )

    if values.dtype != np.int16:
        raise HsrValidationError(
            f"Unexpected HSR dtype: {values.dtype}"
        )

    no_echo = values == HSR_NO_ECHO
    outside = values == HSR_OUTSIDE_OBSERVATION
    undocumented_mask = values == HSR_UNDOCUMENTED_MASK

    special = no_echo | outside | undocumented_mask
    physical = ~special
    physical_values = values[physical]

    if physical_values.size:
        actual_min = int(physical_values.min())
        actual_max = int(physical_values.max())

        if actual_min < minimum_physical_raw:
            raise HsrValidationError(
                "HSR physical value below configured range: "
                f"minimum={actual_min}, "
                f"configured_minimum={minimum_physical_raw}"
            )

        if actual_max > maximum_physical_raw:
            raise HsrValidationError(
                "HSR physical value above configured range: "
                f"maximum={actual_max}, "
                f"configured_maximum={maximum_physical_raw}"
            )
    else:
        actual_min = None
        actual_max = None

    return HsrValidationReport(
        nx=grid.nx,
        ny=grid.ny,
        total_cells=int(values.size),
        no_echo_cells=int(no_echo.sum()),
        outside_cells=int(outside.sum()),
        undocumented_mask_cells=int(undocumented_mask.sum()),
        physical_cells=int(physical.sum()),
        negative_physical_cells=int((physical_values < 0).sum()),
        minimum_physical_raw=actual_min,
        maximum_physical_raw=actual_max,
    )
