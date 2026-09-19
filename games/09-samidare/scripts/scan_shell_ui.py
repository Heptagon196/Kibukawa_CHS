"""Read-only inventory of Japanese Unity shell strings in the ninth game."""
from __future__ import annotations

import json
import struct
from pathlib import Path

import UnityPy

import pipeline as p


def strings(data: bytes):
    for offset in range(0, len(data) - 4, 4):
        length = struct.unpack_from("<I", data, offset)[0]
        if length < 2 or length > 1024 or length > len(data) - offset - 4:
            continue
        try:
            value = data[offset + 4 : offset + 4 + length].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if "\x00" in value or "\n\n\n" in value:
            continue
        yield offset + 4, value


def main():
    known_file = p.SERIES / "games/08-kibu8/work/ui-serialized.zh-CN.json"
    known = {
        entry["source_text"]
        for entry in json.loads(known_file.read_text(encoding="utf-8-sig"))["entries"]
        if entry.get("target_text")
    }
    inputs = [
        p.GAME / "kibu9_Data/level0",
        p.GAME / "kibu9_Data/resources.assets",
        p.GAME / "kibu9_Data/sharedassets0.assets",
    ]
    inputs.extend(
        file
        for file in (p.GAME / "kibu9_Data/StreamingAssets/prefab").glob("*")
        if file.is_file() and file.suffix != ".manifest"
    )
    found = []
    for file in inputs:
        environment = UnityPy.load(str(file))
        for obj in environment.objects:
            if obj.type.name not in {"MonoBehaviour", "TextAsset"}:
                continue
            for offset, value in strings(obj.get_raw_data()):
                has_kana = any("\u3040" <= char <= "\u30ff" for char in value)
                if not has_kana and value not in known:
                    continue
                found.append(
                    {
                        "asset_file": file.relative_to(p.GAME).as_posix(),
                        "path_id": obj.path_id,
                        "object_type": obj.type.name,
                        "byte_offset": offset,
                        "source": value,
                    }
                )
    unique = sorted({item["source"] for item in found})
    report = {"schema": 1, "files": len(inputs), "occurrences": len(found), "unique": len(unique), "strings": unique, "locations": found}
    output = p.WORK / "research/shell-ui-scan.json"
    p.save(output, report)
    print(f"Shell UI scan: {len(unique)} strings, {len(found)} occurrences -> {output}")


if __name__ == "__main__":
    main()
