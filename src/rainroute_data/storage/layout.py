from __future__ import annotations

from pathlib import Path

from rainroute_data.schemas.manifest import DataIdentity


def raw_artifact_path(
    data_root: Path,
    identity: DataIdentity,
    *,
    suffix: str,
) -> Path:
    timestamp = identity.valid_time or identity.issue_time
    if timestamp is None:
        raise ValueError("identity requires valid_time or issue_time")

    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")

    date_path = Path(
        f"{timestamp:%Y}",
        f"{timestamp:%m}",
        f"{timestamp:%d}",
    )

    timestamp_text = timestamp.strftime("%Y%m%dT%H%M%S%z")
    variable = f"_{identity.variable}" if identity.variable else ""
    level = f"_{identity.level}" if identity.level else ""
    filename = (
        f"{identity.product}_{timestamp_text}"
        f"{variable}{level}.{suffix.lstrip('.')}"
    )

    return (
        data_root.expanduser().resolve()
        / "raw"
        / identity.source
        / date_path
        / filename
    )


def manifest_path_for(artifact_path: Path) -> Path:
    return artifact_path.with_name(f"{artifact_path.name}.manifest.json")

