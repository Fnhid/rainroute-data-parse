import pytest

from rainroute_data.validation.precipitation_accumulation import (
    trapezoidal_accumulation_mm,
)


def test_constant_rate_over_15_minutes() -> None:
    accumulation = trapezoidal_accumulation_mm(
        [12.0, 12.0, 12.0, 12.0],
        interval_minutes=5,
    )

    assert accumulation == pytest.approx(3.0)


def test_varying_rate() -> None:
    accumulation = trapezoidal_accumulation_mm(
        [0.0, 6.0, 12.0, 6.0],
        interval_minutes=5,
    )

    expected = (
        (0.0 + 6.0) / 2.0
        + (6.0 + 12.0) / 2.0
        + (12.0 + 6.0) / 2.0
    ) * (5.0 / 60.0)

    assert accumulation == pytest.approx(expected)


def test_rejects_single_sample() -> None:
    with pytest.raises(
        ValueError,
        match="At least two",
    ):
        trapezoidal_accumulation_mm(
            [1.0],
            interval_minutes=5,
        )


def test_rejects_invalid_interval() -> None:
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        trapezoidal_accumulation_mm(
            [1.0, 1.0],
            interval_minutes=0,
        )
