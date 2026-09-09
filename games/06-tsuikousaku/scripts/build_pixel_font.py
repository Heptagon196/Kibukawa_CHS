"""Build a native 16px, monochrome dialogue atlas from GNU Unifont.

No system font rasterizer, resampling, or antialiasing is involved. All writes
stay in the sixth-game project; sibling caches are read-only SHA-256 seeds. The original
Unifont source and its OFL terms accompany the derived, renamed atlas.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import tarfile
import unicodedata
import zlib

WORK = Path(__file__).resolve().parents[1]
ROOT = WORK / "bepinex"
PIXEL_SIZE = 16
PADDING = 1
CELL_SIZE = PIXEL_SIZE + 2 * PADDING


def inside(path):
    path = Path(path).resolve()
    if not path.is_relative_to(WORK):
        raise ValueError(f"Font output must stay inside {WORK}: {path}")
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path = inside(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def save_json(path, value):
    write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def ensure_dependency(item):
    """Use only pinned local bytes; never mutate sibling projects or download."""
    cached = inside(ROOT / "fonts" / item["file"])
    candidates = [cached]
    for name in ("05-kurai-hako", "04-shirasagi", "03-shisha-no-rakuen", "02-kairou", "01-kamen-gensou"):
        candidates.append(WORK.parent / name / "bepinex" / "fonts" / item["file"])
    for candidate in candidates:
        if not candidate.is_file():
            continue
        data = candidate.read_bytes()
        if len(data) == item["size"] and digest(data) == item["sha256"]:
            if candidate != cached:
                write(cached, data)
            return cached, False
    raise ValueError("No SHA-256-verified local font dependency: " + item["file"])


def parse_hex(data):
    glyphs = {}
    for line in gzip.decompress(data).decode("ascii").splitlines():
        code, bits = line.split(":")
        cp = int(code, 16)
        if cp in glyphs or len(bits) not in (32, 64):
            raise ValueError(f"Unsupported/duplicate glyph U+{cp:04X}")
        width = len(bits) // 4
        raw = bytes.fromhex(bits)
        rows = [int.from_bytes(raw[y * (width // 8):(y + 1) * (width // 8)], "big")
                for y in range(16)]
        glyphs[cp] = width, rows
    return glyphs


def required_characters(pack):
    """Collect every printable dialogue character, including half-width text.

    Whitespace with a visible advance (including ordinary/fullwidth spaces) is
    retained. Layout controls such as CR/LF and TAB are
    not drawable glyphs and remain the caller's responsibility.
    """
    required = set(range(0x20, 0x7F)) | set(range(0xFF61, 0xFFA0)) | {0x25A1, 0x3000}
    for entry in [entry for group in ("scripts", "literals", "ui", "localization") for entry in pack.get(group, [])]:
        for key in ("source", "target"):
            for ch in entry.get(key, "") or "":
                cp = ord(ch)
                include = ch.isprintable() or unicodedata.category(ch) == "Zs"
                if include:
                    if cp > 0xFFFF or 0xD800 <= cp <= 0xDFFF:
                        raise ValueError(f"Dialogue contains unsupported non-BMP character U+{cp:X}")
                    required.add(cp)
    # UI and help copy must have bitmap coverage too, even if currently drawn
    # with the runtime UI font. Include every cache target, not just dialogue.
    cache = json.loads((WORK / "work/cache.json").read_text(encoding="utf-8-sig"))
    texts = [item.get(key, "") or "" for group in cache["files"].values() for item in group["items"] for key in ("source_text", "translated_text")]
    from build_help_pages import PAGES
    def strings(value):
        if isinstance(value, str): yield value
        elif isinstance(value, dict):
            for child in value.values(): yield from strings(child)
        elif isinstance(value, list):
            for child in value: yield from strings(child)
    texts.extend(strings(PAGES))
    for value in texts:
        for ch in value:
            if ch.isprintable() or unicodedata.category(ch) == "Zs":
                cp = ord(ch)
                if cp > 0xFFFF or 0xD800 <= cp <= 0xDFFF:
                    raise ValueError(f"Unsupported target character U+{cp:X}")
                required.add(cp)
    return sorted(required)


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def encode_png(width, height, rgba):
    scanlines = b"".join(b"\0" + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scanlines, 9)) + chunk(b"IEND", b""))


def build_font(pack, output):
    """Write out/fonts/dialogue-16.{png,bin}, source and licenses; return report.

    KBF2 consists of ASCII magic, LE int32 pixelSize/width/height/count, then
    count LE int32 codepoint/x/y/nativeWidth records. Coordinates are PNG top-left.
    All glyph cells are exactly 16x16 with a transparent 1px outer gutter.
    Narrow glyphs occupy the left 8 columns without resizing. ASCII, spaces,
    punctuation and halfwidth kana all come from the standard non-JP Unifont.
    """
    out = inside(output)
    lock = json.loads((ROOT / "font-dependency.lock.json").read_text(encoding="utf-8"))
    downloaded = []
    paths = {}
    for key, dependency in lock["dependencies"].items():
        paths[key], fresh = ensure_dependency(dependency)
        if fresh:
            downloaded.append(dependency["file"])
    glyphs = parse_hex(paths["glyphs"].read_bytes())
    chars = required_characters(pack)
    missing = [f"U+{cp:04X} {chr(cp)}" for cp in chars if cp not in glyphs]
    if missing:
        save_json(ROOT / "build" / "pixel-missing.json", {"missing": missing})
        raise ValueError("Native pixel font lacks required characters: " + ", ".join(missing))
    if not chars:
        raise ValueError("No dialogue characters found; refusing an empty pixel atlas")
    # Power-of-two dimensions, fixed 18px cells, no resampling or texture packing rotation.
    width = 1 << (max(256, math.ceil(math.sqrt(len(chars))) * CELL_SIZE) - 1).bit_length()
    columns = width // CELL_SIZE
    height = 1 << (math.ceil(len(chars) / columns) * CELL_SIZE - 1).bit_length()
    rgba = bytearray(width * height * 4)
    index = bytearray(b"KBF2" + struct.pack("<iiii", PIXEL_SIZE, width, height, len(chars)))
    for i, cp in enumerate(chars):
        gx = (i % columns) * CELL_SIZE + PADDING
        gy = (i // columns) * CELL_SIZE + PADDING
        glyph_width, rows = glyphs[cp]
        index.extend(struct.pack("<iiii", cp, gx, gy, glyph_width))
        for y, row in enumerate(rows):
            for x in range(glyph_width):
                if row & (1 << (glyph_width - 1 - x)):
                    offset = ((gy + y) * width + gx + x) * 4
                    rgba[offset:offset + 4] = b"\xff\xff\xff\xff"
    png = encode_png(width, height, rgba)
    write(out / "fonts" / "dialogue-16.png", png)
    write(out / "fonts" / "dialogue-16.bin", index)
    write(out / "fonts" / paths["glyphs"].name, paths["glyphs"].read_bytes())
    # Extract only exact regular files; never extract archive paths wholesale.
    with tarfile.open(paths["source"], "r:gz") as archive:
        for original, name in (("COPYING", "Unifont-COPYING.txt"),
                               ("OFL-1.1.txt", "Unifont-OFL-1.1.txt"),
                               ("README", "Unifont-README.txt")):
            member = archive.getmember(f"unifont-{lock['version']}/{original}")
            if not member.isfile():
                raise ValueError("Unexpected license archive member type")
            content = archive.extractfile(member).read()
            write(ROOT / "licenses" / name, content)
            write(out / "licenses" / name, content)
    notice = ("Kibu6 Dialogue Pixel 16 - a subset/format conversion of GNU Unifont " + lock["version"] + "\n"
              "Font homepage: https://unifoundry.com/unifont/\n"
              "Original glyph designs: GNU Unifont contributors, including Roman Czyborra,\n"
              "Paul Hardy, Qianqian Fang/Wen Quan Yi and other contributors credited\n"
              "in Unifont-README.txt and the upstream source distribution.\n"
              "The font and this derived atlas are distributed under the SIL Open Font\n"
              "License 1.1. See Unifont-OFL-1.1.txt and Unifont-COPYING.txt.\n"
              "Only a subset selection and PNG/KBF2 conversion was performed; each\n"
              "source bitmap pixel is preserved without resampling or antialiasing.\n"
              "The unchanged original .hex.gz is included in fonts/.\n")
    write(ROOT / "licenses" / "Unifont-Atlas-Notice.txt", notice.encode("utf-8"))
    write(out / "licenses" / "Unifont-Atlas-Notice.txt", notice.encode("utf-8"))
    report = {"font": lock["font"], "version": lock["version"], "pixelSize": PIXEL_SIZE,
              "glyphCount": len(chars), "requiredGlyphs": len(chars), "missingGlyphs": [],
              "indexFormat": "KBF2", "variant": "standard (non-JP)",
              "allDialogueGlyphs": True, "allPackGroups": ["scripts", "literals", "ui", "localization"],
              "helpTextCoverage": True, "runtimeUiFont": "OS dynamic CJK font; atlas coverage only",
              "runtimeCellSizes": "Shared LegacyFontRenderer uses StFont.Size, including 12px", "asciiCoverage": "U+0020..U+007E (95/95)",
              "nativeWidths": {str(w): sum(glyphs[cp][0] == w for cp in chars) for w in (8, 16)},
              "coverage": 1.0, "atlasWidth": width, "atlasHeight": height,
              "alphaValues": [0, 255], "resampled": False, "padding": PADDING,
              "sha256": lock["dependencies"]["glyphs"]["sha256"],
              "dependencies": lock["dependencies"], "downloaded": downloaded, "dependencyMode": "verified-local-cache-only",
              "png_sha256": digest(png), "index_sha256": digest(index), "license": "OFL-1.1"}
    save_json(ROOT / "build" / "pixel-font-report.json", report)
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=ROOT / "build/plugin/translations.json")
    parser.add_argument("--out", type=Path, default=ROOT / "build/plugin")
    args = parser.parse_args()
    report = build_font(json.loads(args.pack.read_text(encoding="utf-8")), args.out)
    print(json.dumps(report, ensure_ascii=False, indent=2))
