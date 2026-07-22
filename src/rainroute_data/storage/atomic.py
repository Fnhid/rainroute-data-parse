from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from rainroute_data.schemas.manifest import CollectionManifest


@dataclass(frozen=True)
class WrittenArtifact:
    path: Path
    size_bytes: int
    sha256: str
    created: bool


class AtomicWriteError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_bytes(
    destination: Path,
    data: bytes,
    *,
    overwrite: bool = False,
) -> WrittenArtifact:
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    digest = sha256_bytes(data)

    if destination.exists() and not overwrite:
        existing_digest = sha256_file(destination)
        if existing_digest == digest:
            return WrittenArtifact(
                path=destination,
                size_bytes=destination.stat().st_size,
                sha256=existing_digest,
                created=False,
            )
        raise FileExistsError(
            f"Refusing to replace an existing file with different content: {destination}"
        )

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temp_path, destination)
        _fsync_directory(destination.parent)
    except Exception as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise AtomicWriteError(f"Failed to write {destination}") from exc

    return WrittenArtifact(
        path=destination,
        size_bytes=len(data),
        sha256=digest,
        created=True,
    )


def atomic_write_stream(
    destination: Path,
    source: BinaryIO,
    *,
    overwrite: bool = False,
    chunk_size: int = 1024 * 1024,
) -> WrittenArtifact:
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    digest = hashlib.sha256()
    size_bytes = 0

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temp_path = Path(stream.name)

            while chunk := source.read(chunk_size):
                stream.write(chunk)
                digest.update(chunk)
                size_bytes += len(chunk)

            stream.flush()
            os.fsync(stream.fileno())

        new_digest = digest.hexdigest()

        if destination.exists() and not overwrite:
            existing_digest = sha256_file(destination)
            if existing_digest == new_digest:
                temp_path.unlink(missing_ok=True)
                return WrittenArtifact(
                    path=destination,
                    size_bytes=destination.stat().st_size,
                    sha256=existing_digest,
                    created=False,
                )
            raise FileExistsError(
                f"Refusing to replace an existing file with different content: {destination}"
            )

        os.replace(temp_path, destination)
        _fsync_directory(destination.parent)
    except Exception as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        if isinstance(exc, FileExistsError):
            raise
        raise AtomicWriteError(f"Failed to write {destination}") from exc

    return WrittenArtifact(
        path=destination,
        size_bytes=size_bytes,
        sha256=new_digest,
        created=True,
    )


def atomic_write_manifest(
    destination: Path,
    manifest: CollectionManifest,
    *,
    overwrite: bool = False,
) -> WrittenArtifact:
    payload = json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")
    payload += b"\n"
    return atomic_write_bytes(destination, payload, overwrite=overwrite)

