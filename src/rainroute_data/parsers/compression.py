from __future__ import annotations

import gzip
from dataclasses import dataclass
from pathlib import Path


class CompressionError(ValueError):
    """Raised when a compressed payload cannot be decoded."""


GZIP_MAGIC = b"\x1f\x8b"


@dataclass(frozen=True)
class DecompressedPayload:
    content: bytes
    compression: str
    compressed_size: int
    decompressed_size: int

    @property
    def compression_ratio(self) -> float:
        if self.decompressed_size == 0:
            return 0.0

        return self.compressed_size / self.decompressed_size


def is_gzip_payload(payload: bytes) -> bool:
    return payload.startswith(GZIP_MAGIC)


def decompress_payload(payload: bytes) -> DecompressedPayload:
    if not is_gzip_payload(payload):
        return DecompressedPayload(
            content=payload,
            compression="none",
            compressed_size=len(payload),
            decompressed_size=len(payload),
        )

    try:
        content = gzip.decompress(payload)
    except (OSError, EOFError) as exc:
        raise CompressionError(
            "Payload has a gzip signature but could not be decompressed"
        ) from exc

    return DecompressedPayload(
        content=content,
        compression="gzip",
        compressed_size=len(payload),
        decompressed_size=len(content),
    )


def decompress_file(path: Path) -> DecompressedPayload:
    return decompress_payload(path.read_bytes())
