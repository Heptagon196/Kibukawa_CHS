"""Strict offline parser of CanvasEx's 20050817 VM. Offsets are script-relative.

The version-neutral frame (byte cursor, Shift-JIS decoding, label table, command
loop) lives in gmode-v2; this module owns only what is specific to this version:
the opcode tables, the row/colour/ruby plane layout, and the ZIP+envelope
container envelope.
"""
import struct
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / 'gmode-v2'))
import vm_frame as frame

VERSION = b'20050817'

NAMES = dict(zip([1,2,3,4,5,6,8,12,13,15,16,17,23,24,25,26,27,28,29,32,33,34,39,40,47,48,49,51,52,57,59,60,62,69,72,74,75,80,84,112,113,114,117,118,119,120,240,248,250,255],
    ['TOBU','SABU','MODORU','BUNKI','KOMANDO','CHOUBUN_KOMANDO','SENTAKUSI','RANDAMU','SEEBU','SYUURYOU','IRO','NAMAE_SETTEI','MOJI_IRO','MOJI_ON','HAIKEI_SYOKU','KOMANDO_SYOKU','MOJI_SOKUDO','MOJI_HANI','GAMEN_KIRIKAE','FURAGU','FURAGU_RISETTO','RANSUU','UEITO','HAIKEI_SETTI','NAMAE','KYARA','PreSASIKAE','KUTI','FURASSYU','KYOKU','KYOKU','OTO','KYARA_SETTI','FAIRU','INFO','ROORU','BUNSYOU_ROLL','SIORI','GAMEN_HANTEN','ICON_KOMANDO','ICON_SENTAKUSI','RISUTO','JIYUU_KOMANDO','HANNI','SUKUROORU','BUNSYOU_SCROLL','BUNSYOU_ASTARISK','BUNSYOU_FADE','BUNSYOU_FA','BUNSYOU']))
FORMATS = {1:'h',2:'h',3:'',4:'BBBBBBH',6:'h',8:'sH',12:'H',13:'h',15:'',16:'BBBB',17:'BsssB',23:'B',25:'B',26:'BBBB',27:'h',28:'BB',29:'BH',32:'BBBBB',33:'',34:'BBBB',39:'h',47:'b',48:'shhh',49:'ss',51:'sB',52:'BH',57:'ss',59:'ss',60:'s',62:'shh',69:'s',80:'s',84:'B',112:'',113:'sH',114:'',117:'',118:'BBBBH',119:'B',240:'',248:'h',250:''}
CONTROL_NAMES = {46:'period',58:'colon',59:'semicolon',43:'jingle_plus',37:'jingle_percent',94:'hatto',47:'slash'}

# Re-exported so existing callers keep importing them from this module.
decode_text = frame.decode_text
Reader = frame.Reader


def read_row(reader, kind):
    """Read one display row including its colour, control, ruby and ruby-glyph planes."""
    row = {'offset': reader.pos, 'cells_count': reader.number()}
    n = row['cells_count']
    row['text_offset'] = reader.pos
    raw = reader.take(2 * n)
    row['text'] = frame.decode_text(raw, reader.codec)
    # A display slot holds two encoded bytes: one fullwidth glyph or two halfwidth glyphs.
    row['cells'] = [frame.decode_text(raw[i:i + 2], reader.codec) for i in range(0, len(raw), 2)]
    for plane, present in [('ruby_indices', kind in (255, 75)), ('colors', True), ('controls', kind in (255, 120))]:
        row[plane + '_offset'] = reader.pos if present else None
        row[plane] = list(reader.take(n)) if present else []
        if plane == 'ruby_indices':
            row[plane] = [x if x < 128 else x - 256 for x in row[plane]]
    row['rubies'] = []
    if kind in (255, 75):
        row['ruby_count_offset'] = reader.pos
        count = reader.number()
        for _ in range(count):
            ruby = {'offset': reader.pos, 'base_cells': reader.number(), 'cells_count': reader.number(),
                    'text_offset': reader.pos}
            ruby['bytes'] = list(reader.take(ruby['cells_count'] * 2))
            ruby['end'] = reader.pos
            row['rubies'].append(ruby)
    row['events'] = [{'cell': i, 'offset': row['controls_offset'] + i, 'control': v,
                      'name': CONTROL_NAMES.get(v, 'unknown')}
                     for i, v in enumerate(row['controls']) if v]
    row['end'] = reader.pos
    return row


def _command(reader, command, read):
    if read('B'):
        read('s')
    read('h')


def _moji_on(reader, command, read):
    if read('B'):
        read('s')


def _haikei_setti(reader, command, read):
    if read('B') == 1:
        read('s')
    if read('s'):
        read('h')
        read('h')


def _rooru(reader, command, read):
    if read('B') == 0:
        read('B')


def _bunsyou(reader, command, read):
    lines = read('B')
    read('B')
    command['rows'] = [read_row(reader, command['opcode']) for _ in range(lines)]


def _single_row(reader, command, read):
    command['rows'] = [read_row(reader, command['opcode'])]


SPECIAL = {5: _command, 24: _moji_on, 40: _haikei_setti, 74: _rooru, 255: _bunsyou,
           72: _single_row, 75: _single_row, 120: _single_row}


def parse_script(data, codec='cp932'):
    """Return commands covering every byte; reject unknown opcodes and short operands.

    Each command has offset/end/opcode/name,args,rows. args are typed value records.
    Rows expose exact plane offsets, slot strings (possibly two halfwidth characters),
    integer color/control planes, signed ruby indices, ruby text and control events.
    """
    return frame.parse_commands(data, NAMES, FORMATS, SPECIAL, codec, with_rows=True)


def parse_bin(raw, codec='cp932'):
    """Parse a complete extracted .bin; validate labels against command boundaries.

    Commands/labels are script-relative. Add script_offset for file-relative offsets.
    """
    if raw[:2] != b'\xff\xff' or len(raw) < 17:
        raise ValueError('Invalid envelope')
    if int.from_bytes(raw[2:4], 'little') != len(raw) - 4:
        raise ValueError('Size mismatch')
    labels, script, start = frame.split_script(raw[4:], VERSION)
    commands = parse_script(script, codec)
    frame.validate_labels(labels, commands, len(script))
    return dict(script_offset=4 + start, labels=labels, commands=commands, script_size=len(script))
