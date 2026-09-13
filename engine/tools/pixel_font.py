"""Shared native Unifont bitmap parsing and lossless PNG encoding.

Extracted from the series pixel atlas builders; no filesystem writes or downloads.
"""
import gzip
import struct
import zlib


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


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def encode_png(width, height, rgba):
    scanlines = b"".join(b"\0" + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scanlines, 9)) + chunk(b"IEND", b""))
