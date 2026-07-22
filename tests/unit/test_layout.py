from datetime import UTC, datetime

from rainroute_data.schemas.manifest import DataIdentity
from rainroute_data.storage.layout import manifest_path_for, raw_artifact_path


def test_raw_artifact_path(tmp_path) -> None:
    identity = DataIdentity(
        source="radar_hsp",
        product="HSP",
        valid_time=datetime(2026, 7, 22, 3, 5, tzinfo=UTC),
        variable="rain_rate",
    )

    path = raw_artifact_path(tmp_path, identity, suffix="bin")

    assert path == (
        tmp_path.resolve()
        / "raw/radar_hsp/2026/07/22/HSP_20260722T030500+0000_rain_rate.bin"
    )
    assert manifest_path_for(path).name.endswith(".bin.manifest.json")

