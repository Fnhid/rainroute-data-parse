from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from rainroute_data.schemas.manifest import (
    ArtifactMetadata,
    CollectionManifest,
    CollectionStatus,
    DataIdentity,
    FileFormat,
    RequestMetadata,
)


def test_manifest_round_trip() -> None:
    manifest = CollectionManifest(
        status=CollectionStatus.SUCCESS,
        identity=DataIdentity(
            source="radar_hsp",
            product="HSP",
            valid_time=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
        ),
        request=RequestMetadata(
            url="https://example.invalid/radar",
            requested_at=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
            http_status=200,
        ),
        artifact=ArtifactMetadata(
            relative_path="raw/radar_hsp/2026/07/22/file.bin",
            format=FileFormat.BINARY,
            size_bytes=4,
            sha256="a" * 64,
        ),
    )

    restored = CollectionManifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest


def test_artifact_rejects_absolute_path() -> None:
    with pytest.raises(ValidationError):
        ArtifactMetadata(
            relative_path="/tmp/file.bin",
            format=FileFormat.BINARY,
            size_bytes=1,
            sha256="a" * 64,
        )


def test_manifest_rejects_secret_in_error() -> None:
    with pytest.raises(ValidationError):
        CollectionManifest(
            status=CollectionStatus.FAILED,
            identity=DataIdentity(source="radar_hsp", product="HSP"),
            request=RequestMetadata(
                url="https://example.invalid",
                requested_at=datetime.now(UTC),
            ),
            error_message="request failed: authKey=secret",
        )

