"""Shared KBF2 dialogue-atlas packing for the series pixel font builders.

KBF2 is the 16px monochrome dialogue atlas read by
``engine/adapters/gmode-v2/src/BitmapFontAtlas.cs``: a ``KBF2`` signature, the
pixel size, atlas dimensions and glyph count, then one
``(codepoint, x, y, nativeWidth)`` record per glyph. Glyphs are Unifont rows with
no resampling or antialiasing, so rasterisation is identical on every machine.

This module only packs bytes: the caller picks the character set, verifies the
locked font download and decides where files are written.
"""
import math
import struct

from pixel_font import encode_png

PIXEL_SIZE = 16
CELL_SIZE = 18
PADDING = 1
SIGNATURE = b'KBF2'


def layout(count, cell_size=CELL_SIZE):
    """Pick power-of-two atlas dimensions that hold ``count`` padded cells."""
    width = 1 << (max(256, math.ceil(math.sqrt(count)) * cell_size) - 1).bit_length()
    columns = width // cell_size
    height = 1 << (math.ceil(count / columns) * cell_size - 1).bit_length()
    if width > 8192 or height > 8192:
        raise ValueError('Atlas exceeds the common BitmapFontAtlas dimension limit')
    return width, height, columns


def build(characters, glyphs, pixel_size=PIXEL_SIZE, cell_size=CELL_SIZE, padding=PADDING):
    """Return ``(index, png, coverage)`` for the given codepoints.

    ``characters`` must be a sorted iterable of codepoints; ``glyphs`` is the
    ``{codepoint: (native_width, rows)}`` map from ``engine/tools/pixel_font.parse_hex``.
    """
    missing = ['U+%04X %s' % (cp, chr(cp)) for cp in characters if cp not in glyphs]
    if missing:
        raise ValueError('Native font lacks: ' + ', '.join(missing))
    width, height, columns = layout(len(characters), cell_size)
    rgba = bytearray(width * height * 4)
    index = bytearray(SIGNATURE + struct.pack('<iiii', pixel_size, width, height, len(characters)))
    coverage = []
    for order, cp in enumerate(characters):
        gx = order % columns * cell_size + padding
        gy = order // columns * cell_size + padding
        native_width, rows = glyphs[cp]
        if native_width not in (pixel_size // 2, pixel_size):
            raise ValueError('Unexpected native width for U+%04X' % cp)
        index.extend(struct.pack('<iiii', cp, gx, gy, native_width))
        for y, row in enumerate(rows):
            for x in range(native_width):
                if row & (1 << (native_width - 1 - x)):
                    offset = ((gy + y) * width + gx + x) * 4
                    rgba[offset:offset + 4] = b'\xff' * 4
        coverage.append(dict(codepoint='U+%04X' % cp, character=chr(cp), nativeWidth=native_width))
    return bytes(index), encode_png(width, height, rgba), dict(width=width, height=height, columns=columns,
                                                               glyphs=len(characters), coverage=coverage)


def png_size(png):
    """Read width/height from a PNG IHDR without decoding the image."""
    if png[:8] != b'\x89PNG\r\n\x1a\n' or png[12:16] != b'IHDR':
        raise ValueError('PNG signature mismatch')
    return struct.unpack_from('>II', png, 16)


def validate(index, png, characters, pixel_size=PIXEL_SIZE):
    """Re-read the packed index the way BitmapFontAtlas does and check every invariant."""
    if index[:4] != SIGNATURE:
        raise ValueError('Invalid pixel font signature')
    size, width, height, count = struct.unpack_from('<iiii', index, 4)
    if size != pixel_size or count != len(characters) or len(index) != 20 + count * 16:
        raise ValueError('Pixel font index does not match the requested character set')
    if png_size(png) != (width, height):
        raise ValueError('Pixel font image does not match the atlas dimensions')
    for order in range(count):
        cp, gx, gy, native_width = struct.unpack_from('<iiii', index, 20 + order * 16)
        if cp != characters[order]:
            raise ValueError('Pixel font glyph order mismatch at %d' % order)
        if gx < 0 or gy < 0 or gx + native_width > width or gy + pixel_size > height:
            raise ValueError('Pixel glyph outside the atlas at %d' % order)
    return True
