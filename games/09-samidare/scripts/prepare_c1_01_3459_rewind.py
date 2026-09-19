"""Prepare a verified rewind to c1_01:3459; never writes the live save."""
from __future__ import annotations

import hashlib
import json
import struct
import time
from pathlib import Path

import pipeline as p


TARGET_OFFSET = 3459
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
    if len(original) != 65536:
        raise ValueError("unexpected SaveData container size")
    payload_size = struct.unpack_from(">I", original, 0)[0]
    payload_end = 4 + payload_size
    if payload_end > len(original):
        raise ValueError("invalid payload size")

    current_offset = struct.unpack_from(">i", original, 4)[0]
    values, tail_start = read_strings(original, STRING_START, payload_end)
    if values[0] != "c1_01":
        raise ValueError(f"current save is {values[0]}:{current_offset}, expected c1_01")
    if current_offset < 3497:
        raise ValueError(f"current save {values[0]}:{current_offset} is already before the requested rewind point")

    edited = bytearray(original)
    struct.pack_into(">i", edited, 4, TARGET_OFFSET)
    struct.pack_into(">i", edited, 372, -1)       # internal monologue: no nameplate
    struct.pack_into(">i", edited, 392, 0)        # black background colour
    edited[1905] = 0                              # no named-speaker mouth animation
    values[1] = "停止"                            # music has faded out before this line
    values[2] = ""
    values[43] = ""                              # the scene is fully faded to black
    values[44:49] = ["", "", "", "", ""]

    payload = bytes(edited[4:STRING_START]) + encode_strings(values) + original[tail_start:payload_end]
    if len(payload) + 4 > len(original):
        raise ValueError("rewound payload exceeds the fixed container")
    output = bytearray(original)
    struct.pack_into(">I", output, 0, len(payload))
    output[4:4 + len(payload)] = payload
    output[4 + len(payload):payload_end] = b"\0" * max(0, payload_size - len(payload))

    verify_end = 4 + struct.unpack_from(">I", output, 0)[0]
    verify_values, _ = read_strings(output, STRING_START, verify_end)
    if struct.unpack_from(">i", output, 4)[0] != TARGET_OFFSET:
        raise AssertionError("target instruction did not persist")
    if struct.unpack_from(">i", output, 372)[0] != -1:
        raise AssertionError("speaker state did not persist")
    if struct.unpack_from(">i", output, 392)[0] != 0:
        raise AssertionError("background colour did not persist")
    if verify_values[0:3] != ["c1_01", "停止", ""]:
        raise AssertionError("scenario or music verification failed")
    if verify_values[43:49] != ["", "", "", "", "", ""]:
        raise AssertionError("black-scene visual verification failed")

    folder = p.inside(p.WORK / "backups" / ("save_rewind_c1_01_3459_" + time.strftime("%Y%m%d_%H%M%S")))
    folder.mkdir(parents=True)
    backup = folder / "SaveData.original"
    staged = folder / "SaveData.before-age-line"
    backup.write_bytes(original)
    staged.write_bytes(output)
    changed = [index for index, pair in enumerate(zip(original, output)) if pair[0] != pair[1]]
    report = {
        "target": str(source),
        "backup": str(backup),
        "staged": str(staged),
        "source_sha256": sha(original),
        "staged_sha256": sha(output),
        "source_entry": f"c1_01:{current_offset}",
        "entry": "c1_01:3459",
        "target_text": "我明明才２５岁／啊…",
        "restored_state": {
            "speaker": "旁白（无名牌）",
            "background": "黑场",
            "characters": [],
            "music": "停止"
        },
        "changed_byte_count": len(changed),
        "preserved": "flags, choices, names, colours, rain state, and all unrelated save fields",
        "installed": False
    }
    (folder / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    p.save(p.WORK / "reports/c1-01-3459-rewind-latest.json", report)
    print("PREPARED", staged)
    print("BACKUP", backup)
    print("ENTRY", report["source_entry"], "->", report["entry"])
    print("SHA256", report["source_sha256"], "->", report["staged_sha256"])


if __name__ == "__main__":
    main()
