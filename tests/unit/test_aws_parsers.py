from datetime import datetime

import pytest

from rainroute_data.parsers.aws_minute import (
    parse_aws_minute_text,
)
from rainroute_data.parsers.aws_stations import (
    parse_aws_stations_text,
)


def test_parse_aws_stations() -> None:
    text = """
# STN LON LAT
42 126.59722000 35.93638000 other fields
95 127.30420000 38.14787000 other fields
"""

    stations = parse_aws_stations_text(text)

    assert stations[42].longitude == pytest.approx(126.59722)
    assert stations[42].latitude == pytest.approx(35.93638)
    assert stations[95].latitude == pytest.approx(38.14787)


def test_parse_aws_minute() -> None:
    text = """
# header
202607221905,95,239.1,0.6,239.1,1.2,239.1,0.3,26.0,-99.9,1.0,2.7,8.4,8.4,98.0,989.9,1007.4,25.7,=
"""

    observations = parse_aws_minute_text(text)
    observation = observations[0]

    assert observation.observed_at == datetime(2026, 7, 22, 19, 5)
    assert observation.station_id == 95
    assert observation.rain_15m_mm == pytest.approx(1.0)
    assert observation.rain_60m_mm == pytest.approx(2.7)


def test_missing_precipitation_becomes_none() -> None:
    text = """
202607221905,116,0,0,0,0,0,0,0,-99.9,-99.9,-99.9,-99.9,-99.2,0,0,0,0,=
"""

    observation = parse_aws_minute_text(text)[0]

    assert observation.rain_15m_mm is None
    assert observation.rain_60m_mm is None
    assert observation.rain_day_mm is None
