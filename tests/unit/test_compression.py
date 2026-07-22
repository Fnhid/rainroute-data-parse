import gzip

import pytest

from rainroute_data.parsers.compression import (
    CompressionError,
    decompress_payload,
    is_gzip_payload,
)


def test_decompresses_gzip_payload() -> None:
    original = b"rainroute-hsp-grid"
    payload = gzip.compress(original, mtime=0)

    result = decompress_payload(payload)

    assert result.compression == "gzip"
    assert result.content == original
    assert result.compressed_size == len(payload)
    assert result.decompressed_size == len(original)


def test_returns_uncompressed_payload_unchanged() -> None:
    payload = b"plain-binary"

    result = decompress_payload(payload)

    assert result.compression == "none"
    assert result.content == payload
    assert result.compressed_size == len(payload)
    assert result.decompressed_size == len(payload)


def test_detects_gzip_magic() -> None:
    assert is_gzip_payload(b"\x1f\x8b\x08\x00")
    assert not is_gzip_payload(b"plain")


def test_rejects_invalid_gzip_payload() -> None:
    with pytest.raises(CompressionError):
        decompress_payload(b"\x1f\x8bnot-valid-gzip")
