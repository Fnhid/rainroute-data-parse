from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainroute_data.clients.kma import KmaClient
from rainroute_data.schemas.manifest import (
    ArtifactMetadata,
    CollectionManifest,
    CollectionStatus,
    DataIdentity,
    FileFormat,
    RequestMetadata,
)
from rainroute_data.storage.atomic import (
    atomic_write_bytes,
    atomic_write_manifest,
)
from rainroute_data.storage.layout import manifest_path_for


class RawResponseCollector:
    def __init__(
        self,
        *,
        client: KmaClient,
        data_root: Path,
    ) -> None:
        self._client = client
        self._data_root = data_root.expanduser().resolve()

    def collect(
        self,
        *,
        identity: DataIdentity,
        endpoint: str,
        params: dict[str, Any],
        destination: Path,
        file_format: FileFormat,
        content_type_override: str | None = None,
    ) -> CollectionManifest:
        destination = destination.expanduser().resolve()

        try:
            relative_path = destination.relative_to(self._data_root)
        except ValueError as exc:
            raise ValueError(
                "destination must be inside data_root"
            ) from exc

        requested_at = datetime.now(UTC)

        response = self._client.get(
            endpoint,
            params=params,
        )

        completed_at = datetime.now(UTC)

        artifact = atomic_write_bytes(
            destination,
            response.content,
        )

        status = (
            CollectionStatus.SUCCESS
            if artifact.created
            else CollectionStatus.DUPLICATE
        )

        manifest = CollectionManifest(
            status=status,
            identity=identity,
            request=RequestMetadata(
                method="GET",
                url=response.request_url,
                params=response.request_params,
                requested_at=requested_at,
                completed_at=completed_at,
                http_status=response.status_code,
                elapsed_ms=response.elapsed_ms,
                attempt=1,
            ),
            artifact=ArtifactMetadata(
                relative_path=relative_path.as_posix(),
                format=file_format,
                size_bytes=artifact.size_bytes,
                sha256=artifact.sha256,
                content_type=(
                    content_type_override
                    if content_type_override is not None
                    else response.content_type
                ),
            ),
        )

        manifest_path = manifest_path_for(destination)

        # The original success manifest is immutable. A repeated identical
        # request returns DUPLICATE to the caller without rewriting it.
        if artifact.created or not manifest_path.exists():
            atomic_write_manifest(
                manifest_path,
                manifest,
            )

        return manifest
