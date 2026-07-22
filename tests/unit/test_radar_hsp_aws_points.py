from datetime import datetime

import pytest

from rainroute_data.parsers.radar_hsp_aws_points import (
    parse_hsp_aws_points_text,
)


def test_parse_physical_hsp_point() -> None:
    text = """
# header
202607221910,95,HSP,EXT,6.710,98.0,철원,,=
"""

    point = parse_hsp_aws_points_text(text)[0]

    assert point.observed_at == datetime(2026, 7, 22, 19, 10)
    assert point.station_id == 95
    assert point.product == "HSP"
    assert point.quality_code == "EXT"
    assert point.echo_mm_h == pytest.approx(6.71)
    assert point.status == "physical"
    assert point.echo_height_m == pytest.approx(98.0)
    assert point.station_name == "철원"


def test_parse_no_rain_sentinel() -> None:
    text = """
202607221910,42,HSP,EXT,-250.000,175.9,군산오식도,,=
"""

    point = parse_hsp_aws_points_text(text)[0]

    assert point.echo_mm_h is None
    assert point.status == "no_rain"


def test_parse_outside_sentinel() -> None:
    text = """
202607221910,42,HSP,EXT,-300.000,-300.0,테스트,,=
"""

    point = parse_hsp_aws_points_text(text)[0]

    assert point.echo_mm_h is None
    assert point.status == "outside_observation"
    assert point.echo_height_m is None
