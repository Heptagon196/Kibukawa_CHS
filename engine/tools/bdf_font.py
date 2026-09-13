"""Shared native BDF parser; no resampling or game dependencies."""
def parse_bdf(data, advances=(6, 12)):
    """Read native 12px BDF including overhangs; never resize or clip glyphs."""
    glyphs = {}
    for block in data.decode('utf-8').split('STARTCHAR ')[1:]:
        lines = block.splitlines()
        props = {line.split()[0]: line.split()[1:] for line in lines if line}
        cp = int(props['ENCODING'][0])
        if cp < 0:
            continue
        native_width, advance_y = map(int, props['DWIDTH'])
        box = tuple(map(int, props['BBX']))
        box_width, box_height, bearing_x, bearing_y = box
        if native_width not in advances or advance_y != 0:
            continue
        start = lines.index('BITMAP') + 1
        raw_rows = lines[start:lines.index('ENDCHAR')]
        if len(raw_rows) != box_height:
            raise ValueError('BDF row count differs from BBX')
        shift = ((box_width + 7) // 8) * 8 - box_width
        rows = [int(row, 16) >> shift for row in raw_rows]
        if any(int(row, 16) & ((1 << shift) - 1) for row in raw_rows):
            raise ValueError('Nonzero BDF alignment padding')
        glyphs[cp] = native_width, box_width, box_height, bearing_x, bearing_y, rows
    return glyphs
