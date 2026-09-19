"""Build the ninth game's 16px dialogue and 12px shell/UI atlases offline.

Character coverage comes from the work's own data only: the tagged translation
draft, the UI localization file, and the fixed punctuation/box-drawing set the
runtime always needs. The 16px Unifont KBF2 packing and 12px Z Labs KBF3 source
and encoding are shared with the eighth game. Every dependency is verified from
the pinned local cache on each run.
"""
import gzip
import hashlib
import html
import json
import math
import re
import struct
import sys
import tarfile
import unicodedata
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
SERIES = WORK.parents[1]
sys.path.insert(0, str(SERIES / 'engine/tools'))
sys.path.insert(0, str(SERIES / 'engine/fonts'))
sys.path.insert(0, str(SERIES / 'tools'))
from pixel_font import encode_png, parse_hex
import kbf2_atlas
from kbf3_atlas import encode_kbf3
from project_config import resolve
from zlabs_font import load_glyphs, load_source, native_alpha

PROJECT = resolve(project=WORK, allow_disabled=True)
TAG = re.compile(r'<(?:/?color(?:=[^>]*)?|ctrl=[^>]*|row/|boundary=[^>]*/)>')
# Characters the runtime draws even when no translation uses them yet.
FIXED_TEXT = '　□（）【】「」『』、。・…—―！？：；'
BASELINE = set(range(0x20, 0x7F)) | set(range(0xFF01, 0xFF5F)) | set(range(0xFF61, 0xFFA0)) | {0x25A1, 0x3000}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inside(path):
    path = Path(path).resolve()
    if not path.is_relative_to(WORK) or path == WORK:
        raise ValueError('Output outside the ninth-game project')
    return path


def write(path, data):
    path = inside(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def dependency(item):
    """Find the locked font file locally (this work or a sibling) or download it."""
    cached = inside(WORK / 'bepinex/fonts' / item['file'])
    candidates = [cached] + [p / 'bepinex/fonts' / item['file']
                             for p in sorted(WORK.parent.iterdir(), reverse=True) if p != WORK and p.is_dir()]
    for path in candidates:
        if not path.is_file() or path.stat().st_size != item['size']:
            continue
        data = path.read_bytes()
        if digest(data) != item['sha256']:
            continue
        if path != cached:
            write(cached, data)
        return cached
    import urllib.request
    request = urllib.request.Request(item['url'], headers={'User-Agent': 'Kibukawa-CHS-Build/1.0'})
    with urllib.request.urlopen(request, timeout=180) as response:
        data = response.read(item['size'] + 1)
    if len(data) != item['size'] or digest(data) != item['sha256']:
        raise ValueError('Font source mismatch: ' + item['file'])
    return write(cached, data)


def display_codepoint(cp):
    if 0xFF01 <= cp <= 0xFF5E:
        return cp - 0xFEE0
    if 0xFF61 <= cp <= 0xFF9F:
        return cp - 0xFEC0
    return cp


def collect(draft=None, ui_paths=None):
    draft = Path(draft) if draft else WORK / 'work/dialogue-tagged.json'
    ui_paths = [Path(p) for p in ui_paths] if ui_paths else sorted((WORK / 'work').glob('ui-*.json'))
    required = set(BASELINE)
    provenance = {cp: {'baseline'} for cp in BASELINE}
    for ch in FIXED_TEXT:
        required.add(ord(ch))
        provenance.setdefault(ord(ch), set()).add('fixed')
    inputs = []
    for path in [draft, *ui_paths]:
        if not path.is_file():
            continue
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8-sig'))
        records = document.get('units') if 'units' in document else document.get('entries', [])
        for index, entry in enumerate(records):
            for key in ('source', 'target'):
                value = entry.get(key)
                if value is None and key == 'target':
                    value = entry.get('target_text')
                if value is None and key == 'source':
                    value = entry.get('source_text')
                if not isinstance(value, str):
                    continue
                for ch in TAG.sub('', html.unescape(value)):
                    if not (ch.isprintable() or unicodedata.category(ch) == 'Zs'):
                        continue
                    cp = ord(ch)
                    if cp > 0xFFFF or 0xD800 <= cp <= 0xDFFF:
                        raise ValueError('Unsupported non-BMP glyph U+%X at %s:%d' % (cp, path.name, index))
                    for rendered in {cp, display_codepoint(cp)}:
                        required.add(rendered)
                        provenance.setdefault(rendered, set()).add(path.name)
        inputs.append({'path': path.name, 'sha256': digest(raw), 'entries': len(records)})
    return sorted(required), inputs, provenance


def validate_small_font(folder, characters, glyphs):
    index = (folder / 'dialogue-16.bin').read_bytes()
    if index[:4] != b'KBF3':
        raise ValueError('Small-font KBF3 signature mismatch')
    pixel_size, width, height, count = struct.unpack_from('<iiii', index, 4)
    if pixel_size != 12 or count != len(characters) or len(index) != 20 + count * 32:
        raise ValueError('Small-font KBF3 dimensions mismatch')
    for i, cp in enumerate(characters):
        record = struct.unpack_from('<iiiiiiii', index, 20 + i * 32)
        if record[0] != cp or record[3:] != glyphs[cp][:5]:
            raise ValueError('Small-font KBF3 metrics mismatch at U+%04X' % cp)
        if record[1] < 1 or record[2] < 1 or record[1] + record[4] >= width or record[2] + record[5] >= height:
            raise ValueError('Small-font glyph outside atlas at U+%04X' % cp)
    return dict(indexFormat='KBF3', pixelSize=12, glyphCount=count, width=width, height=height,
                nativePixelsPreserved=True, nativeMetricsPreserved=True)


def build_small_font(out, characters, inputs):
    lock, _ = load_source()  # verifies the shared pinned KBITX and OFL cache
    glyphs = load_glyphs()
    missing = [cp for cp in characters if cp not in glyphs]
    if missing:
        raise ValueError('Z Labs Pixel 12px lacks: ' + ', '.join('U+%04X %s' % (cp, chr(cp)) for cp in missing))
    cell = max(max(glyphs[cp][1:3]) for cp in characters) + 2
    width = 1 << (max(256, math.ceil(math.sqrt(len(characters))) * cell) - 1).bit_length()
    columns = width // cell
    height = 1 << (math.ceil(len(characters) / columns) * cell - 1).bit_length()
    records = []
    for i, cp in enumerate(characters):
        gx, gy = i % columns * cell + 1, i // columns * cell + 1
        advance, bitmap_width, bitmap_height, bearing_x, bearing_y, rows = glyphs[cp]
        alpha = bytes(native_alpha(cp, x, y) if rows[y] & (1 << (bitmap_width - 1 - x)) else 0
                      for y in range(bitmap_height) for x in range(bitmap_width))
        records.append((cp, gx, gy, advance, bitmap_width, bitmap_height,
                        bearing_x, bearing_y, alpha))
    index, rgba = encode_kbf3(12, width, height, records)
    folder = out / 'ui-12'
    write(folder / 'dialogue-16.bin', index)
    write(folder / 'dialogue-16.png', encode_png(width, height, rgba))
    validation = validate_small_font(folder, characters, glyphs)
    report = dict(font=lock['font'], version=lock['version'], pixelSize=12, indexFormat='KBF3',
                  glyphCount=len(characters), fontAscent=10, fontDescent=2,
                  nativeWidths={str(n): sum(glyphs[cp][0] == n for cp in characters) for n in (6, 12)},
                  inputs=inputs, dependencies=lock['dependencies'], validation=validation,
                  index_sha256=digest(index), png_sha256=digest((folder / 'dialogue-16.png').read_bytes()))
    write(folder / 'glyph-coverage.json', json.dumps(report, ensure_ascii=False, indent=1).encode('utf-8'))
    license_bytes = (SERIES / 'engine/fonts/cache/ZLabs-OFL.txt').read_bytes()
    write(out / 'licenses/ZLabs-OFL.txt', license_bytes)
    notice = ('Kibu9 UI Pixel 12 is a subset and format conversion of Z Labs Pixel 12px M CN.\n'
              'Copyright Astro_2539. Licensed under OFL-1.1; see ZLabs-OFL.txt.\n'
              'Native KBITX pixels, advances, bounds and bearings are preserved without scaling.\n')
    write(out / 'licenses/ZLabs-Atlas-Notice.txt', notice.encode('utf-8'))
    return report


def build(output=None, draft=None):
    out = inside(output if output is not None else WORK / 'bepinex/build/pack/fonts')
    lock = load(WORK / 'bepinex/font-dependency.lock.json')
    paths = {key: dependency(item) for key, item in lock['dependencies'].items()}
    glyphs = parse_hex(paths['glyphs'].read_bytes())
    characters, inputs, provenance = collect(draft)
    index, png, report = kbf2_atlas.build(characters, glyphs)
    kbf2_atlas.validate(index, png, characters)
    write(out / 'dialogue-16.bin', index)
    write(out / 'dialogue-16.png', png)
    small = build_small_font(out, characters, inputs)
    write(out / 'font-dependency.lock.json', (WORK / 'bepinex/font-dependency.lock.json').read_bytes())
    if paths['source'].is_file():
        with tarfile.open(paths['source'], 'r:gz') as archive:
            for original, name in [('COPYING', 'Unifont-COPYING.txt'), ('OFL-1.1.txt', 'Unifont-OFL-1.1.txt'),
                                   ('README', 'Unifont-README.txt')]:
                member = archive.getmember('unifont-%s/%s' % (lock['version'], original))
                content = archive.extractfile(member).read()
                write(WORK / 'bepinex/licenses' / name, content)
                write(out / 'licenses' / name, content)
    notice = ('Kibu9 Dialogue Pixel 16 - a subset and format conversion of GNU Unifont %s.\n'
              'Original glyphs: GNU Unifont contributors including Roman Czyborra, Paul Hardy and\n'
              'Qianqian Fang/Wen Quan Yi; see Unifont-README.txt for credits.\n'
              'Homepage: https://unifoundry.com/unifont/\n'
              'Distributed under SIL Open Font License 1.1.\n'
              'The derived atlas preserves native bitmap pixels without resampling or antialiasing.\n' % lock['version'])
    write(out / 'licenses/Unifont-Atlas-Notice.txt', notice.encode('utf-8'))
    inputs.append({'path': 'fixed', 'sha256': digest(FIXED_TEXT.encode('utf-8')), 'entries': len(FIXED_TEXT)})
    result = dict(font=lock['font'], version=lock['version'], pixelSize=kbf2_atlas.PIXEL_SIZE,
                  indexFormat='KBF2', glyphCount=report['glyphs'], width=report['width'], height=report['height'],
                  atlas_sha256=digest(index), png_sha256=digest(png), inputs=inputs,
                  smallFont=small, runtime_tested=False)
    write(out.parent / 'font-report.json', json.dumps(result, ensure_ascii=False, indent=1).encode('utf-8'))
    print('FONT READY %d glyphs, %dx%d -> %s' % (report['glyphs'], report['width'], report['height'], out))
    return result


if __name__ == '__main__':
    build()
