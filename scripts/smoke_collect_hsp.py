from __future__ import annotations

import argparse
import os
import struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from rainroute_data.clients.kma import KmaClient
from rainroute_data.collectors.radar_hsp import collect_hsp_file
from rainroute_data.collectors.raw_response import RawResponseCollector
from rainroute_data.parsers.compression import decompress_payload
from rainroute_data.schemas.manifest import DataIdentity
from rainroute_data.storage.layout import raw_artifact_path

KST = ZoneInfo("Asia/Seoul")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--time",
        required=True,
        help="HSP observation time in KST: YYYYMMDDHHMM",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = os.environ.get("KMA_API_KEY")
    data_root_text = os.environ.get("RAINROUTE_DATA_ROOT")

    if not api_key:
        raise SystemExit("KMA_API_KEY is not set")

    if not data_root_text:
        raise SystemExit("RAINROUTE_DATA_ROOT is not set")

    data_root = Path(data_root_text).expanduser().resolve()

    valid_time = datetime.strptime(
        args.time,
        "%Y%m%d%H%M",
    ).replace(tzinfo=KST)

    with KmaClient(api_key=api_key) as client:
        collector = RawResponseCollector(
            client=client,
            data_root=data_root,
        )

        manifest = collect_hsp_file(
            collector=collector,
            data_root=data_root,
            valid_time=valid_time,
        )

    identity = DataIdentity(
        source="radar_hsp",
        product="HSP",
        valid_time=valid_time,
        variable="rain_rate",
        grid="HSP_native",
    )

    path = raw_artifact_path(
        data_root,
        identity,
        suffix="bin",
    )

    compressed_payload = path.read_bytes()
    decompressed = decompress_payload(compressed_payload)
    payload = decompressed.content
    prefix = payload[:64]

    print(f"status={manifest.status}")
    print(f"path={path}")
    print(f"compression={decompressed.compression}")
    print(f"compressed_size_bytes={decompressed.compressed_size}")
    print(f"decompressed_size_bytes={decompressed.decompressed_size}")
    print(
        "compression_ratio="
        f"{decompressed.compression_ratio:.8f}"
    )
    print(f"inner_first_64_hex={prefix.hex()}")
    print(f"inner_first_64_ascii={prefix!r}")

    if len(payload) >= 4:
        print(
            "inner_header_little_hh="
            f"{struct.unpack('<hh', payload[:4])}"
        )
        print(
            "inner_header_big_hh="
            f"{struct.unpack('>hh', payload[:4])}"
        )
        print(
            "inner_header_little_i="
            f"{struct.unpack('<i', payload[:4])}"
        )
        print(
            "inner_header_big_i="
            f"{struct.unpack('>i', payload[:4])}"
        )

    if manifest.artifact is not None:
        print(f"sha256={manifest.artifact.sha256}")
        print(f"content_type={manifest.artifact.content_type}")


if __name__ == "__main__":
    main()
