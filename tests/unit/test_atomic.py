from io import BytesIO

import pytest

from rainroute_data.storage.atomic import (
    atomic_write_bytes,
    atomic_write_stream,
    sha256_file,
)


def test_atomic_write_bytes_creates_file(tmp_path) -> None:
    destination = tmp_path / "sample.bin"
    result = atomic_write_bytes(destination, b"rainroute")

    assert result.created is True
    assert destination.read_bytes() == b"rainroute"
    assert result.sha256 == sha256_file(destination)


def test_identical_write_is_deduplicated(tmp_path) -> None:
    destination = tmp_path / "sample.bin"
    atomic_write_bytes(destination, b"same")

    result = atomic_write_bytes(destination, b"same")

    assert result.created is False
    assert destination.read_bytes() == b"same"


def test_different_content_is_rejected(tmp_path) -> None:
    destination = tmp_path / "sample.bin"
    atomic_write_bytes(destination, b"first")

    with pytest.raises(FileExistsError):
        atomic_write_bytes(destination, b"second")


def test_atomic_write_stream(tmp_path) -> None:
    destination = tmp_path / "sample.bin"
    result = atomic_write_stream(destination, BytesIO(b"streamed"))

    assert result.created is True
    assert destination.read_bytes() == b"streamed"

