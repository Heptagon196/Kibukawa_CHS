"""Build native 16px Unifont KBF2 and 12px Z Labs Pixel KBF3 atlases offline.

API: build_font(output=ROOT / 'build/plugin', dialogue=None, ui_paths=None).
Both source fallback and translated display text are covered. ASCII remains
available at native width; its fullwidth display counterparts are also included.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re
import struct
import sys
import tarfile
import unicodedata
import zlib
import zipfile

WORK = Path(__file__).resolve().parents[1]
SERIES = WORK.parents[1]
ROOT = WORK / 'bepinex'
sys.path.insert(0, str(SERIES / 'engine/tools'))
from pixel_font import encode_png, parse_hex
from kbf3_atlas import encode_kbf3
from bdf_font import parse_bdf
from zlabs_font import load_glyphs, load_source, native_alpha

PIXEL_SIZE, PADDING, CELL_SIZE = 16, 1, 18
TAG = re.compile(r'<(?:/?color(?:=[^>]*)?|ctrl=[^>]*|row/)>')
FIXED_UI_TEXT = '注释收起打开笔记本（）'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inside(path):
    path = Path(path).resolve()
    if not path.is_relative_to(WORK):
        raise ValueError('Font output must remain in eighth-game project: ' + str(path))
    return path


def write(path, data):
    path = inside(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def save_json(path, value):
    write(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def display_codepoint(cp):
    """The adapter can map ASCII to these full-cell glyphs before atlas lookup."""
    if cp == 0x20:
        return 0x3000
    return cp + 0xFEE0 if 0x21 <= cp <= 0x7E else cp


def collect_characters(dialogue=None, ui_paths=None, ui_only=False):
    dialogue = Path(dialogue) if dialogue else WORK / 'work/dialogue-tagged.json'
    ui_paths = list(map(Path, ui_paths)) if ui_paths is not None else sorted((WORK / 'work').glob('ui-*.json'))
    inputs, provenance = [], {}
    required = set(range(0x20, 0x7F)) | set(range(0xFF61, 0xFFA0)) | {0x25A1, 0x3000}
    required.update(display_codepoint(cp) for cp in range(0x20, 0x7F))
    for ch in FIXED_UI_TEXT:
        required.add(ord(ch))
        provenance.setdefault(ord(ch), set()).add('fixed-ui:注释收起')
    for path in [dialogue, *ui_paths]:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8-sig'))
        records = document['units'] if path == dialogue else document['entries']
        accepted = 0
        for index, entry in enumerate(records):
            if ui_only and path == dialogue and entry.get('opcode') in (255,75,120) and 'sousamemo' not in entry.get('script',''):
                continue
            accepted += 1
            keys = ('source', 'target') if path == dialogue else ('source_text', 'target_text')
            # Exclusion means "do not patch this string", not "never drawable".
            # Preserve glyph coverage for every original string, including
            # templates, technical sentinels and original names in loaded saves.
            if str(entry.get('classification', '')).startswith('excluded'):
                keys = keys[:1]
            for key in keys:
                value = entry.get(key)
                if value is None:
                    continue
                if not isinstance(value, str):
                    raise ValueError(f'Non-string display text: {path}:{index}:{key}')
                value = html.unescape(TAG.sub('', value))
                for ch in value:
                    if not (ch.isprintable() or unicodedata.category(ch) == 'Zs'):
                        continue
                    cp = ord(ch)
                    if cp > 0xFFFF or 0xD800 <= cp <= 0xDFFF:
                        raise ValueError(f'Unsupported non-BMP glyph U+{cp:X} at {path}:{index}:{key}')
                    for rendered in {cp, display_codepoint(cp)}:
                        required.add(rendered)
                        provenance.setdefault(rendered, set()).add(path.name)
        inputs.append({'path': str(path.relative_to(WORK)), 'sha256': digest(raw), 'entries': accepted})
    return sorted(required), inputs, provenance


def required_characters(dialogue=None, ui_paths=None):
    return collect_characters(dialogue, ui_paths)[0]


def dependency(item):
    cached = inside(ROOT / 'fonts' / item['file'])
    candidates = [cached] + [p / 'bepinex/fonts' / item['file'] for p in sorted(WORK.parent.iterdir(), reverse=True) if p != WORK and p.is_dir()]
    for path in candidates:
        if not path.is_file() or path.stat().st_size != item['size']:
            continue
        data = path.read_bytes()
        if digest(data) != item['sha256']:
            continue
        if path != cached:
            write(cached, data)
        return cached
    raise ValueError('No verified local font dependency: ' + item['file'] +
                     '; run games/08-kibu8/scripts/fetch_pixel_font.py first')


def decode_png(data):
    """Decode this builder's RGBA PNGs without a platform font/image dependency."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('PNG signature mismatch')
    position, compressed, size = 8, bytearray(), None
    while position < len(data):
        length = struct.unpack_from('>I', data, position)[0]
        kind = data[position + 4:position + 8]
        payload = data[position + 8:position + 8 + length]
        crc = struct.unpack_from('>I', data, position + 8 + length)[0]
        assert zlib.crc32(kind + payload) == crc
        if kind == b'IHDR':
            w, h, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            assert (depth, color, compression, filtering, interlace) == (8, 6, 0, 0, 0)
            size = w, h
        elif kind == b'IDAT':
            compressed.extend(payload)
        position += length + 12
    assert size is not None
    w, h = size
    raw = zlib.decompress(compressed)
    assert len(raw) == h * (w * 4 + 1)
    assert all(raw[y * (w * 4 + 1)] == 0 for y in range(h))
    pixels = b''.join(raw[y * (w * 4 + 1) + 1:(y + 1) * (w * 4 + 1)] for y in range(h))
    return w, h, pixels


def validate_font(output, chars, glyphs, pixel_size=16, atlas=None):
    out = inside(output)
    atlas = inside(atlas) if atlas is not None else out / 'fonts'
    data = (atlas / 'dialogue-16.bin').read_bytes()
    assert data[:4] == b'KBF2'
    size, width, height, count = struct.unpack_from('<iiii', data, 4)
    assert size == pixel_size and len(data) == 20 + count * 16
    assert 16 <= width <= 8192 and 16 <= height <= 8192
    w, h, pixels = decode_png((atlas / 'dialogue-16.png').read_bytes())
    assert (w, h) == (width, height)
    records = [struct.unpack_from('<iiii', data, 20 + i * 16) for i in range(count)]
    assert [r[0] for r in records] == chars
    assert len(set((r[1], r[2]) for r in records)) == count
    for cp, gx, gy, native_width in records:
        assert 0 < gx and gx + pixel_size < w and 0 < gy and gy + pixel_size < h
        source_width, rows = glyphs[cp]
        assert native_width == source_width
        for y in range(-1, pixel_size + 1):
            for x in range(-1, pixel_size + 1):
                ink = 0 <= y < pixel_size and 0 <= x < native_width and rows[y] & (1 << (native_width - 1 - x))
                offset = ((gy + y) * w + gx + x) * 4
                assert pixels[offset:offset + 4] == (b'\xff' * 4 if ink else b'\0' * 4), (cp, x, y)
    return {'glyphs': count, 'missing_glyphs': [], 'native_pixels_preserved': True,
            'transparent_padding_verified': True, 'binary_and_png_verified': True,
            'ascii_fullwidth_display_coverage': '95/95', 'runtime_tested': False}



def validate_ui_font(atlas, chars, glyphs):
    data = (atlas / 'dialogue-16.bin').read_bytes()
    assert data[:4] == b'KBF3'
    size, width, height, count = struct.unpack_from('<iiii', data, 4)
    assert size == 12 and count == len(chars) and len(data) == 20 + count * 32
    w, h, pixels = decode_png((atlas / 'dialogue-16.png').read_bytes())
    assert (w, h) == (width, height)
    for i, cp in enumerate(chars):
        code, x, y, advance, bw, bh, bx, by = struct.unpack_from('<iiiiiiii', data, 20 + i * 32)
        assert code == cp and (advance, bw, bh, bx, by) == glyphs[cp][:5]
        assert x > 0 and y > 0 and x + bw < w and y + bh < h
        rows = glyphs[cp][5]
        for dy in range(-1, bh + 1):
            for dx in range(-1, bw + 1):
                ink = 0 <= dy < bh and 0 <= dx < bw and rows[dy] & (1 << (bw - 1 - dx))
                offset = ((y + dy) * w + x + dx) * 4
                assert pixels[offset:offset + 4] == (bytes((255,255,255,native_alpha(cp,dx,dy))) if ink else b'\0' * 4), (cp, dx, dy)
    return {'glyphs': count, 'native_pixels_preserved': True, 'transparent_padding_verified': True,
            'binary_and_png_verified': True, 'runtime_tested': False}


def load_ui_glyphs(lock=None, out=None):
    glyphs = load_glyphs()
    if out is not None:
        write(out/'licenses/ZLabs-OFL.txt', (SERIES/'engine/fonts/licenses/ZLabs-OFL.txt').read_bytes())
    return glyphs, {cp:'Z Labs Pixel 12px M CN' for cp in glyphs}


def build_ui_font(out, chars, inputs, provenance):
    lock_path = SERIES / 'engine/fonts/zlabs-12px.lock.json'
    lock = load(lock_path)
    glyphs, regions = load_ui_glyphs(lock, out)
    missing = [f'U+{cp:04X} {chr(cp)}' for cp in chars if cp not in glyphs]
    if missing:
        save_json(ROOT / 'build/ui-pixel-missing.json', {'missing': missing})
        raise ValueError('Native Z Labs Pixel 12px lacks: ' + ', '.join(missing))
    cell = max(max(glyphs[cp][1:3]) for cp in chars) + 2
    width = 1 << (max(256, math.ceil(math.sqrt(len(chars))) * cell) - 1).bit_length()
    columns = width // cell
    height = 1 << (math.ceil(len(chars) / columns) * cell - 1).bit_length()
    records = []
    for i, cp in enumerate(chars):
        gx, gy = i % columns * cell + 1, i // columns * cell + 1
        advance, bitmap_width, bitmap_height, bearing_x, bearing_y, rows = glyphs[cp]
        alpha = bytes(native_alpha(cp,x,y) if rows[y] & (1 << (bitmap_width-1-x)) else 0
                      for y in range(bitmap_height) for x in range(bitmap_width))
        records.append((cp,gx,gy,advance,bitmap_width,bitmap_height,bearing_x,bearing_y,alpha))
    index, rgba = encode_kbf3(12,width,height,records)
    # The runtime atlas constructor takes a directory and retains these filenames.
    atlas = out / 'fonts/ui-12'
    write(atlas / 'dialogue-16.png', encode_png(width, height, rgba))
    write(atlas / 'dialogue-16.bin', index)
    validation = validate_ui_font(atlas, chars, glyphs)
    report = {'font': lock['font'], 'version': lock['version'], 'pixelSize': 12,
              'indexFormat': 'KBF3', 'fontAscent': 10, 'fontDescent': 2, 'glyphCount': len(chars), 'requiredGlyphs': len(chars),
              'missingGlyphs': [], 'resampled': False, 'nativeWidths': {str(n): sum(glyphs[c][0] == n for c in chars) for n in (6, 12)},
              'fallbackGlyphs': [{'codepoint': f'U+{cp:04X}', 'character': chr(cp), 'member': regions[cp]} for cp in chars if regions[cp] != 'Z Labs Pixel 12px M CN'],
              'inputs': inputs, 'dependencies': lock['dependencies'], 'validation': validation,
              'png_sha256': digest((atlas / 'dialogue-16.png').read_bytes()), 'index_sha256': digest(index)}
    save_json(out / 'fonts/ui-12/glyph-coverage.json', report)
    notice = ('Kibu8 UI Pixel 12 is a subset and format conversion of Z Labs Pixel 12px M CN.\n'
              'Copyright Astro_2539. Licensed under OFL-1.1; see ZLabs-OFL.txt.\n'
              'Source: https://github.com/Astro-2539/ZLabs-Pixel-12px\n'
              'Native KBITX pixels, advance, bounds and bearings preserved without scaling.\n'
              'No modified glyphs or mixed-font supplements are included.\n')
    write(out/'licenses/ZLabs-Atlas-Notice.txt', notice.encode('utf-8'))
    save_json(ROOT / 'build/ui-pixel-font-report.json', report)
    return report


def build_font(output=None, dialogue=None, ui_paths=None):
    out = inside(output if output is not None else ROOT / 'build/plugin')
    lock = load(ROOT / 'font-dependency.lock.json')
    paths = {key: dependency(item) for key, item in lock['dependencies'].items()}
    glyphs = parse_hex(paths['glyphs'].read_bytes())
    chars, inputs, provenance = collect_characters(dialogue, ui_paths)
    missing = [f'U+{cp:04X} {chr(cp)}' for cp in chars if cp not in glyphs]
    if missing:
        save_json(ROOT / 'build/pixel-missing.json', {'missing': missing})
        raise ValueError('Native font lacks: ' + ', '.join(missing))
    width = 1 << (max(256, math.ceil(math.sqrt(len(chars))) * CELL_SIZE) - 1).bit_length()
    columns = width // CELL_SIZE
    height = 1 << (math.ceil(len(chars) / columns) * CELL_SIZE - 1).bit_length()
    if width > 8192 or height > 8192:
        raise ValueError('Atlas exceeds common BitmapFontAtlas dimension limit')
    rgba = bytearray(width * height * 4)
    index = bytearray(b'KBF2' + struct.pack('<iiii', 16, width, height, len(chars)))
    coverage = []
    for i, cp in enumerate(chars):
        gx, gy = i % columns * CELL_SIZE + PADDING, i // columns * CELL_SIZE + PADDING
        native_width, rows = glyphs[cp]
        index.extend(struct.pack('<iiii', cp, gx, gy, native_width))
        for y, row in enumerate(rows):
            for x in range(native_width):
                if row & (1 << (native_width - 1 - x)):
                    offset = ((gy + y) * width + gx + x) * 4
                    rgba[offset:offset + 4] = b'\xff' * 4
        coverage.append({'codepoint': f'U+{cp:04X}', 'character': chr(cp), 'nativeWidth': native_width,
                         'sources': sorted(provenance.get(cp, {'baseline'}))})
    png = encode_png(width, height, rgba)
    write(out / 'fonts/dialogue-16.png', png)
    write(out / 'fonts/dialogue-16.bin', index)
    write(out / 'fonts' / paths['glyphs'].name, paths['glyphs'].read_bytes())
    write(out / 'fonts/font-dependency.lock.json', (ROOT / 'font-dependency.lock.json').read_bytes())
    with tarfile.open(paths['source'], 'r:gz') as archive:
        for original, name in [('COPYING', 'Unifont-COPYING.txt'), ('OFL-1.1.txt', 'Unifont-OFL-1.1.txt'), ('README', 'Unifont-README.txt')]:
            member = archive.getmember(f'unifont-{lock["version"]}/{original}')
            if not member.isfile():
                raise ValueError('Unexpected license archive member type')
            content = archive.extractfile(member).read()
            write(ROOT / 'licenses' / name, content)
            write(out / 'licenses' / name, content)
    notice = (f'Kibu8 Dialogue Pixel 16 - a subset and format conversion of GNU Unifont {lock["version"]}.\n'
              'Original glyphs: GNU Unifont contributors including Roman Czyborra, Paul Hardy,\n'
              'Qianqian Fang/Wen Quan Yi; see Unifont-README.txt for credits.\n'
              'Homepage: https://unifoundry.com/unifont/\n'
              'Distributed under SIL Open Font License 1.1; see Unifont-OFL-1.1.txt and Unifont-COPYING.txt.\n'
              'The derived atlas preserves native bitmap pixels without resampling or antialiasing.\n'
              'ASCII and its fullwidth counterparts are separate unchanged upstream glyphs.\n'
              'The series repository retains the source download lock; upstream font sources are build inputs.\n')
    write(ROOT / 'licenses/Unifont-Atlas-Notice.txt', notice.encode('utf-8'))
    write(out / 'licenses/Unifont-Atlas-Notice.txt', notice.encode('utf-8'))
    validation = validate_font(out, chars, glyphs)
    report = {'font': lock['font'], 'version': lock['version'], 'indexFormat': 'KBF2',
              'pixelSize': 16, 'glyphCount': len(chars), 'requiredGlyphs': len(chars), 'missingGlyphs': [],
              'coverage': 1.0, 'inputs': inputs, 'glyphs': coverage, 'atlasWidth': width, 'atlasHeight': height,
              'nativeWidths': {str(n): sum(glyphs[c][0] == n for c in chars) for n in (8, 16)},
              'asciiDisplayMapping': 'U+0020 -> U+3000; U+0021..U+007E -> codepoint + 0xFEE0; source ASCII retained',
              'asciiDisplayCoverage': '95/95', 'dependencyMode': 'verified-local-cache-only',
              'sourceCoverage': 'All source/source_text entries, including excluded UI entries',
              'fixedUiText': FIXED_UI_TEXT,
              'dependencies': lock['dependencies'], 'license': 'OFL-1.1', 'alphaValues': [0, 255],
              'resampled': False, 'padding': 1, 'png_sha256': digest(png), 'index_sha256': digest(index),
              'validation': validation, 'runtime_tested': False}
    save_json(ROOT / 'build/pixel-font-report.json', report)
    save_json(out / 'font-validation.json', validation)
    save_json(out / 'fonts/glyph-coverage.json', report)
    ui_chars, ui_inputs, ui_provenance = collect_characters(dialogue, ui_paths, ui_only=True)
    report['uiFont'] = build_ui_font(out, ui_chars, ui_inputs, ui_provenance)
    save_json(ROOT / 'build/pixel-font-report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/plugin')
    parser.add_argument('--dialogue', type=Path)
    parser.add_argument('--ui', type=Path, nargs='*', default=None)
    args = parser.parse_args()
    report = build_font(args.out, args.dialogue, args.ui)
    print(json.dumps({k: v for k, v in report.items() if k != 'glyphs'}, ensure_ascii=False, indent=2))
