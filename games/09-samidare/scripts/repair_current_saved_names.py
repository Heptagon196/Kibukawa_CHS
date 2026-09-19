"""One-off repair for the user's current 0.1.7-era Kibu9 SaveData.

The native file is a four-byte big-endian payload length followed by a stream of
primitive values and NUL-terminated CP932 strings.  This script validates the
current scenario marker and all 20 alternating name/image strings before it
changes anything, rebuilds that one variable-length section, and keeps the
65,536-byte container size unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import struct
from pathlib import Path


BROKEN_NAMES = [
    "（凉二）", "（伊", "（癸生川）", "（", "（", "（泉）", "（慧美）", "（莉沙）", "（", "（男性）",
    "（少年）", "（女性）", "（", "（男性）", "（生王）", "（我）", "（慧美母", "（慧美父", "（男性）", "（慧美）",
]
NAME_IMAGES = [
    "ryo", "izu", "kib", "str", "tad", "izm", "sat", "aya", "ayk", "tad",
    "izm", "aya", "str", "ryo", "xxx", "str", "xxx", "xxx", "kib", "sac",
]
SOURCE_NAMES = [
    "(涼二)", "(伊綱)", "(癸生川)", "(螻川内)", "(螻川内)", "(泉)", "(慧美)", "(莉沙)", "(綾子)", "(男性)",
    "(少年)", "(女性)", "(暁)", "(男性)", "(生王)", "(私)", "(慧美の母)", "(慧美の父)", "(男性)", "(慧美)",
]
SCENARIO_MARKER = b"c0_00\0se_rain2\0\0"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_cstring(data: bytes, position: int, end: int) -> tuple[str, int]:
    stop = data.find(b"\0", position, end)
    if stop < 0:
        raise ValueError("unterminated CP932 string")
    return data[position:stop].decode("cp932"), stop + 1


def repair(data: bytes) -> tuple[bytes, int, int]:
    if len(data) != 65536:
        raise ValueError(f"unexpected SaveData container size: {len(data)}")
    payload_size = struct.unpack_from(">I", data, 0)[0]
    payload_end = 4 + payload_size
    if payload_end > len(data) or any(data[payload_end:]):
        raise ValueError("invalid payload length or nonzero container padding")
    marker = data.find(SCENARIO_MARKER, 4, payload_end)
    if marker < 0 or data.find(SCENARIO_MARKER, marker + 1, payload_end) >= 0:
        raise ValueError("current c0_00 save marker missing or ambiguous")
    names_start = marker + len(SCENARIO_MARKER)
    position = names_start
    actual_names: list[str] = []
    actual_images: list[str] = []
    for _ in range(20):
        name, position = read_cstring(data, position, payload_end)
        image, position = read_cstring(data, position, payload_end)
        actual_names.append(name)
        actual_images.append(image)
    if actual_names != BROKEN_NAMES:
        raise ValueError(f"saved name array no longer matches the reviewed fixture: {actual_names!r}")
    if actual_images != NAME_IMAGES:
        raise ValueError(f"saved name image array no longer matches the reviewed fixture: {actual_images!r}")

    replacement = bytearray()
    for name, image in zip(SOURCE_NAMES, NAME_IMAGES):
        replacement += name.encode("cp932") + b"\0"
        replacement += image.encode("cp932") + b"\0"
    payload = data[4:names_start] + replacement + data[position:payload_end]
    if len(payload) + 4 > len(data):
        raise ValueError("repaired payload exceeds the fixed container")
    output = bytearray(len(data))
    struct.pack_into(">I", output, 0, len(payload))
    output[4:4 + len(payload)] = payload

    verify_position = names_start
    verified_names: list[str] = []
    for expected_image in NAME_IMAGES:
        name, verify_position = read_cstring(output, verify_position, 4 + len(payload))
        image, verify_position = read_cstring(output, verify_position, 4 + len(payload))
        if image != expected_image:
            raise AssertionError("rebuilt name/image alignment changed")
        verified_names.append(name)
    if verified_names != SOURCE_NAMES:
        raise AssertionError("rebuilt names failed verification")
    return bytes(output), payload_size, len(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("save_data", type=Path)
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    source = args.save_data.resolve()
    backup = args.backup.resolve()
    original = source.read_bytes()
    fixed, old_size, new_size = repair(original)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        raise FileExistsError(backup)
    shutil.copy2(source, backup)
    temporary = source.with_name(source.name + ".codex-tmp")
    temporary.write_bytes(fixed)
    os.replace(temporary, source)
    installed = source.read_bytes()
    if installed != fixed:
        raise IOError("installed SaveData differs from verified repair")
    print(f"REPAIRED {source}")
    print(f"PAYLOAD {old_size} -> {new_size}")
    print(f"SHA256 {sha(original)} -> {sha(fixed)}")
    print(f"BACKUP {backup}")


if __name__ == "__main__":
    main()
