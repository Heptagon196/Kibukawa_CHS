"""Verify KBF2 against pinned Unifont bitmaps and render a mixed-script specimen.

This is an offline font specimen, not a capture of the game. No user images or
game files are edited. Pass --build to first produce an isolated font output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

from PIL import Image

WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORK / "scripts"))
import build_pixel_font as font


def validate(pack, out, report_path, preview_path):
    data = (out / "fonts/dialogue-16.bin").read_bytes()
    assert data[:4] == b"KBF2", "Expected width-aware KBF2"
    size, width, height, count = struct.unpack_from("<iiii", data, 4)
    assert size == 16 and len(data) == 20 + count * 16
    records = [struct.unpack_from("<iiii", data, 20 + i * 16) for i in range(count)]
    table = {cp: (x, y, native_width) for cp, x, y, native_width in records}
    required = font.required_characters(pack)
    assert len(table) == count and sorted(table) == required
    assert all(cp in table for cp in range(0x20, 0x7F))
    assert all(cp in table for cp in range(0xFF61, 0xFFA0))
    assert 0x3000 in table and 0x25A1 in table
    assert all(table[cp][2] == 8 for cp in range(0x20, 0x7F))
    assert all(table[cp][2] == 8 for cp in range(0xFF61, 0xFFA0))
    lock = json.loads((font.ROOT / "font-dependency.lock.json").read_text("utf-8"))
    source = (font.ROOT / "fonts" / lock["dependencies"]["glyphs"]["file"]).read_bytes()
    assert font.digest(source) == lock["dependencies"]["glyphs"]["sha256"]
    glyphs = font.parse_hex(source)
    atlas = Image.open(out / "fonts/dialogue-16.png").convert("RGBA")
    assert atlas.size == (width, height)
    assert set(atlas.getchannel("A").tobytes()) == {0, 255}
    nonzero = 0
    blank_glyphs = []
    for cp, x, y, native_width in records:
        expected_width, rows = glyphs[cp]
        assert native_width in (8, 16) and native_width == expected_width
        assert x >= 1 and y >= 1 and x + 16 < width and y + 16 < height
        lit = 0
        for dy in range(-1, 17):
            for dx in range(-1, 17):
                expected = (0 <= dy < 16 and 0 <= dx < native_width and
                            bool(rows[dy] & (1 << (native_width - 1 - dx))))
                rgba = atlas.getpixel((x + dx, y + dy))
                assert rgba == ((255, 255, 255, 255) if expected else (0, 0, 0, 0)), (
                    f"Pixel or gutter mismatch U+{cp:04X} ({dx},{dy})")
                lit += int(expected)
        nonzero += lit
        if not lit:
            blank_glyphs.append(f"U+{cp:04X}")
    assert atlas.getchannel("A").histogram()[255] == nonzero, "Stray pixels outside glyphs"
    assert "U+0020" in blank_glyphs and "U+3000" in blank_glyphs
    # Ordinary/full-width spaces must survive; layout control codes must not.
    fixture = {"scripts": [{"source": "A1 。\u3000ｱ", "target": "中\n"}]}
    mixed = font.required_characters(fixture)
    assert 0x20 in mixed and 0x3000 in mixed and 0xFF71 in mixed and 10 not in mixed
    # Render actual atlas masks at the game's 8/16px advance, then integer 3x.
    lines = ["我叫生王正生。", "是一名自由剧本作家。", "初夏的阳光晒得额头冒汗，",
             "RPG 2004/12/6 01:30", "ABC xyz 0123456789", "!?.,:;+-*/()[]{}", "「中文」：100% □", "ｱｲｳｴｵ　A B"]
    specimen = Image.new("RGBA", (272, 8 * 20 + 16), (0, 0, 0, 255))
    for row, line in enumerate(lines):
        pen = 8
        for ch in line:
            cp = ord(ch)
            assert cp in table, f"Specimen glyph missing U+{cp:04X}"
            x, y, native_width = table[cp]
            tile = atlas.crop((x, y, x + native_width, y + 16))
            advance = 8 if 0x20 <= cp <= 0x7E or 0xFF66 <= cp <= 0xFF9F else 16
            specimen.alpha_composite(tile, (pen + (advance - native_width) // 2, 8 + row * 20))
            pen += advance
    preview_path = font.inside(preview_path)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    specimen.convert("RGB").resize((specimen.width * 3, specimen.height * 3), Image.Resampling.NEAREST).save(preview_path)
    report = {"passed": True, "indexFormat": "KBF2", "glyphsPixelVerified": count,
              "asciiGlyphsVerified": 95, "halfwidthKanaGlyphsVerified": 63,
              "nativeWidthsVerified": [8, 16], "alphaValues": [0, 255],
              "asciiAndHalfwidthKanaNativeWidth": 8, "fallbackSquareVerified": True,
              "transparentSpacesVerified": True, "blankGlyphs": blank_glyphs,
              "printableCharactersCovered": True, "sourceSha256": font.digest(source),
              "preview": str(preview_path), "previewType": "offline atlas specimen; not game screenshot"}
    font.save_json(report_path, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=font.ROOT / "build/plugin/translations.json")
    parser.add_argument("--out", type=Path, default=font.ROOT / "build/unifont-all-glyphs-check")
    parser.add_argument("--report", type=Path, default=font.ROOT / "build/unifont-all-glyphs-validation.json")
    parser.add_argument("--preview", type=Path, default=font.ROOT / "build/unifont-mixed-preview.png")
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    pack = json.loads(args.pack.read_text("utf-8"))
    if args.build:
        font.build_font(pack, args.out)
    print(json.dumps(validate(pack, args.out, args.report, args.preview), ensure_ascii=False, indent=2))
