"""Prepare a verified one-off rewind to c1_00:11151; never writes the live save."""
from __future__ import annotations

import hashlib
import json
import struct
import time
from pathlib import Path

import pipeline as p


EXPECTED_SHA256 = "d36b877869141552d3096e2424e8e866af9d0d36cfd7ff6297fc252da5c73826"
TARGET_OFFSET = 11151
STRING_START = 1906
STRING_COUNT = 49


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_strings(data: bytes, start: int, end: int) -> tuple[list[str], int]:
    values = []
    position = start
    for _ in range(STRING_COUNT):
        stop = data.find(b"\0", position, end)
        if stop < 0:
            raise ValueError("unterminated CP932 save string")
        values.append(data[position:stop].decode("cp932"))
        position = stop + 1
    return values, position


def encode_strings(values: list[str]) -> bytes:
    return b"".join(value.encode("cp932") + b"\0" for value in values)


def main() -> None:
    source = p.GAME / "save/SaveData"
    original = source.read_bytes()
    if sha(original) != EXPECTED_SHA256:
        raise ValueError("SaveData changed since the reviewed snapshot")
    if len(original) != 65536:
        raise ValueError("unexpected SaveData container size")
    payload_size = struct.unpack_from(">I", original, 0)[0]
    payload_end = 4 + payload_size
    if payload_end > len(original):
        raise ValueError("invalid payload size")
    if struct.unpack_from(">i", original, 4)[0] != 13319:
        raise ValueError("current continue offset is no longer c1_00:13319")

    values, tail_start = read_strings(original, STRING_START, payload_end)
    if values[0] != "c1_00" or values[1:3] != ["se_rain2", ""]:
        raise ValueError("unexpected scenario or music state")
    if values[43] != "bg05.jpg" or values[44:49] != ["kib_nom", "", "", "", ""]:
        raise ValueError("unexpected saved background or character state")
    if struct.unpack_from(">i", original, 372)[0] != -1:
        raise ValueError("unexpected current speaker state")
    if struct.unpack_from(">ii", original, 664) != (52, 25):
        raise ValueError("unexpected current character position")

    edited = bytearray(original)
    struct.pack_into(">i", edited, 4, TARGET_OFFSET)
    struct.pack_into(">i", edited, 372, 7)       # 莉沙 nameplate
    struct.pack_into(">i", edited, 664, -16)     # pre-transition character X
    edited[1905] = 1                              # named speaker mouth state
    values[1] = "停止"                            # the source fades music before this line
    values[44] = "aya_nom"                       # 莉沙 portrait

    payload = bytes(edited[4:STRING_START]) + encode_strings(values) + original[tail_start:payload_end]
    if len(payload) + 4 > len(original):
        raise ValueError("rewound payload exceeds the fixed container")
    output = bytearray(original)
    struct.pack_into(">I", output, 0, len(payload))
    output[4:4 + len(payload)] = payload
    output[4 + len(payload):payload_end] = b"\0" * (payload_size - len(payload))

    verify_end = 4 + struct.unpack_from(">I", output, 0)[0]
    verify_values, _ = read_strings(output, STRING_START, verify_end)
    if struct.unpack_from(">i", output, 4)[0] != TARGET_OFFSET:
        raise AssertionError("target instruction did not persist")
    if struct.unpack_from(">i", output, 372)[0] != 7:
        raise AssertionError("speaker state did not persist")
    if struct.unpack_from(">ii", output, 664) != (-16, 25):
        raise AssertionError("character position did not persist")
    if verify_values[0:3] != ["c1_00", "停止", ""]:
        raise AssertionError("scenario or music verification failed")
    if verify_values[43:45] != ["bg05.jpg", "aya_nom"]:
        raise AssertionError("visual state verification failed")

    folder = p.inside(p.WORK / "backups" / ("save_rewind_risa_" + time.strftime("%Y%m%d_%H%M%S")))
    folder.mkdir(parents=True)
    backup = folder / "SaveData.original"
    staged = folder / "SaveData.before-risa-line"
    backup.write_bytes(original)
    staged.write_bytes(output)
    changed = [index for index, pair in enumerate(zip(original, output)) if pair[0] != pair[1]]
    report = {
        "target": str(source),
        "backup": str(backup),
        "staged": str(staged),
        "source_sha256": sha(original),
        "staged_sha256": sha(output),
        "entry": "c1_00:11151",
        "target_text": "虽然这和刚才说的无关，",
        "restored_state": {
            "speaker": "莉沙",
            "background": "bg05.jpg",
            "character": "aya_nom",
            "character_xy": [-16, 25],
            "music": "停止"
        },
        "changed_byte_count": len(changed),
        "preserved": "flags, choices, names, colours, rain state, and all unrelated save fields",
        "installed": False
    }
    (folder / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    p.save(p.WORK / "reports/risa-rewind-latest.json", report)
    print("PREPARED", staged)
    print("BACKUP", backup)
    print("SHA256", report["source_sha256"], "->", report["staged_sha256"])


if __name__ == "__main__":
    main()
