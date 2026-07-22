from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CollectionStatus(StrEnum):
    SUCCESS = "success"
    DUPLICATE = "duplicate"
    FAILED = "failed"


class FileFormat(StrEnum):
    BINARY = "binary"
    ASCII = "ascii"
    GRIB = "grib"
    NETCDF = "netcdf"
    JSON = "json"
    XML = "xml"
    TEXT = "text"
    UNKNOWN = "unknown"


class RequestMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = "GET"
    url: str
    params: dict[str, str | int | float | bool] = Field(default_factory=dict)
    requested_at: datetime
    completed_at: datetime | None = None
    http_status: int | None = None
    elapsed_ms: int | None = Field(default=None, ge=0)
    attempt: int = Field(default=1, ge=1)

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str) -> str:
        return value.upper()


class ArtifactMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    format: FileFormat
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_type: str | None = None

    @field_validator("relative_path")
    @classmethod
    def require_relative_path(cls, value: str) -> str:
        path = Path(value)

        if path.is_absolute():
            raise ValueError("relative_path must not be absolute")

        if ".." in path.parts:
            raise ValueError("relative_path must not traverse parent directories")

        return path.as_posix()


class DataIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    product: str
    issue_time: datetime | None = None
    valid_time: datetime | None = None
    lead_hour: int | None = Field(default=None, ge=0)
    variable: str | None = None
    level: str | None = None
    grid: str | None = None


class CollectionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    status: CollectionStatus
    identity: DataIdentity
    request: RequestMetadata
    artifact: ArtifactMetadata | None = None
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("error_message")
    @classmethod
    def reject_secrets(cls, value: str | None) -> str | None:
        if value is None:
            return value

        lowered = value.lower()

        if "authkey=" in lowered or "kma_api_key" in lowered:
            raise ValueError("error_message appears to contain a secret")

        return value
