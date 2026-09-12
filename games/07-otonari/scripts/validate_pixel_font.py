"""Check packaged glyph coverage, native pixels, padding and runtime cell fit offline."""
import argparse
import json
from pathlib import Path
import struct

from PIL import Image
from build_pixel_font import ROOT, build_font, inside, parse_hex, required_characters, save_json


def validate(pack, output):
    output = inside(output)
    data = (output / 'fonts/dialogue-16.bin').read_bytes()
    if data[:4] != b'KBF2':
        raise ValueError('Invalid bitmap font index')
    size, width, height, count = struct.unpack_from('<iiii', data, 4)
    assert size == 16 and len(data) == 20 + 16 * count
    atlas = Image.open(output / 'fonts/dialogue-16.png').convert('RGBA')
    assert atlas.size == (width, height)
    lock = json.loads((ROOT / 'font-dependency.lock.json').read_text(encoding='utf-8'))
    glyphs = parse_hex((output / 'fonts' / lock['dependencies']['glyphs']['file']).read_bytes())
    records = [struct.unpack_from('<iiii', data, 20 + 16 * i) for i in range(count)]
    assert len({row[0] for row in records}) == count
    assert {row[0] for row in records} == set(required_characters(pack))
    occupied = set()
    for cp, gx, gy, native_width in records:
        assert 0 < gx and gx + 16 < width and 0 < gy and gy + 16 < height
        original_width, rows = glyphs[cp]
        assert native_width == original_width
        for y in range(-1, 17):
            for x in range(-1, 17):
                bit = 0 <= y < 16 and 0 <= x < native_width and rows[y] & (1 << (native_width - 1 - x))
                assert atlas.getpixel((gx + x, gy + y)) == ((255, 255, 255, 255) if bit else (0, 0, 0, 0)), (cp, x, y)
        assert (gx, gy) not in occupied
        occupied.add((gx, gy))
        # The common renderer advances ASCII and U+FF66..FF9F by half a cell.
        # Verify each bitmap fits the unchanged advance at both game sizes.
        half = 0x20 <= cp <= 0x7e or 0xff66 <= cp <= 0xff9f
        for runtime_size in (12, 16):
            assert native_width * runtime_size / 16 <= runtime_size / (2 if half else 1)
    labels = json.loads((ROOT / 'display-labels.json').read_text(encoding='utf-8'))['labels']
    label_growth = [row for row in labels if len(row['target']) > len(row['source'])]
    report = dict(glyphs=count, missing_glyphs=[], native_pixels_preserved=True,
                  transparent_padding_verified=True, runtime_cell_sizes=[12, 16],
                  glyph_cell_overflows=0, display_label_growth=label_growth,
                  scope='Glyphs fit legacy cells; dialogue reflow and Unity UI rectangles require their separate checks.')
    save_json(output / 'font-validation.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=ROOT / 'build/plugin/translations.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'build/font-check')
    parser.add_argument('--existing', action='store_true')
    args = parser.parse_args()
    pack = json.loads(args.pack.read_text(encoding='utf-8-sig'))
    if not args.existing:
        build_font(pack, args.out)
    print(json.dumps(validate(pack, args.out), ensure_ascii=False, indent=2))
