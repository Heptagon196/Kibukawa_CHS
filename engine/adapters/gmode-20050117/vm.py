"""Strict offline parser of the ninth title's 20050117 scenario VM.

Offsets are script-relative. The opcode table and every operand layout were
recovered from the shipped ``Assembly-CSharp.dll``: the two ``switch`` tables in
``CanvasEx::Game_adv`` give the dispatch numbers, and each handler's
``ByteRead``/``ShortRead``/``UnsignedShortRead``/``StringRead`` sequence gives
the operand layout. All 14 shipped scenario images replay byte-for-byte and
every label table entry lands on a command boundary.

The version-neutral frame (byte cursor, Shift-JIS decoding, label table, command
loop) lives in gmode-v2; this module owns only the deltas against 20050817:
a bare (envelope-free) scenario image, the extra and removed opcodes, and the
different text model.

This is an older text model than 20050817. ``BUNSYOU`` does not carry per-row
colour, ruby and control planes; it carries three setup bytes plus one
NUL-terminated string, and the surrounding commands (``BUNSYOU_IRO``,
``BUNSYOU_SPEED``, ``BUNSYOU_RUBI``, ``BUNSYOU_FADE``, the punctuation
terminators) change the state that ``CanvasEx::BunsyouStock`` records per
character. Do not reuse the 20050817 row model here.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / 'gmode-v2'))
import vm_frame as frame

VERSION = b'20050117'
# scn0.bin carries its own marker and no label table or script region.
INDEX_VERSION = b'20050524'

NAMES = {
    1: 'TOBU', 2: 'SABU', 3: 'MODORU', 4: 'BUNKI', 5: 'KOMANDO', 6: 'CHOUBUN_KOMANDO',
    8: 'SENTAKUSI', 12: 'RANDAMU', 13: 'SEEBU', 15: 'SYUURYOU', 16: 'IRO', 17: 'NAMAE_SETTEI',
    23: 'MOJI_IRO', 24: 'MOJI_ON', 25: 'HAIKEI_SYOKU', 26: 'KOMANDO_SYOKU', 27: 'MOJI_SOKUDO',
    28: 'MOJI_HANI', 29: 'GAMEN_KIRIKAE', 32: 'FURAGU', 33: 'FURAGU_RISETTO', 34: 'RANSUU',
    39: 'UEITO', 40: 'HAIKEI_SETTI', 47: 'NAMAE', 48: 'KYARA', 49: 'PreSASIKAE', 51: 'KUTI',
    52: 'FURASSYU', 57: 'KYOKU', 59: 'KYOKU', 60: 'OTO', 62: 'KYARA_SETTI', 69: 'FAIRU',
    70: 'AME', 71: 'AME_SETTI',
    240: 'BUNSYOU_ASTARISK', 241: 'BUNSYOU_PERIOD', 242: 'BUNSYOU_COLON',
    243: 'BUNSYOU_SEMI_COLON', 244: 'BUNSYOU_SLASH', 245: 'BUNSYOU_IRO',
    246: 'BUNSYOU_RUBI', 247: 'BUNSYOU_F7', 248: 'BUNSYOU_FADE', 249: 'BUNSYOU_SPEED',
    250: 'BUNSYOU_FA', 255: 'BUNSYOU',
}

# Fixed operand layouts. 's' is a NUL-terminated Shift-JIS string, 'b'/'h'/'H'
# are signed/signed/unsigned 16-bit big-endian values, 'B' is one unsigned byte.
FORMATS = {
    1: 'h', 2: 'h', 3: '', 4: 'BBBBBBH', 5: 'h', 6: 'h', 8: 'sH', 12: 'H', 13: 'h', 15: '',
    16: 'BBBB', 17: 'BsssB', 23: 'B', 25: 'B', 26: 'BBBB', 27: 'h', 28: 'BB', 29: 'BH',
    32: 'BBBBB', 33: '', 34: 'BBBB', 39: 'h', 47: 'b', 48: 'shhh', 49: 'ss', 51: 'sB',
    52: 'BH', 57: 'ss', 59: 'ss', 60: 's', 62: 'shh', 69: 's', 70: 'B', 71: 'BBB',
    240: '', 241: '', 242: '', 243: '', 244: '', 245: 'B', 246: 'sB', 247: '', 248: 'h',
    249: 'h', 250: '', 255: 'BBBs',
}
# Handlers whose operands are conditional rather than a fixed layout.
MOJI_ON = 24
HAIKEI_SETTI = 40
BUNSYOU = 255
BUNSYOU_RUBI = 246
# Commands that carry displayable text: SENTAKUSI's label and NAMAE_SETTEI's nameplate
# are their first StringRead operand, so a text pack can address them by offset.
SENTAKUSI = 8
NAMAE_SETTEI = 17


def _moji_on(reader, command, read):
    if read('B'):
        read('s')


def _haikei_setti(reader, command, read):
    if read('B') == 1:
        read('s')


SPECIAL = {MOJI_ON: _moji_on, HAIKEI_SETTI: _haikei_setti}

# Re-exported so callers and tests import the decode helper from the adapter.
decode_text = frame.decode_text
Reader = frame.Reader


def parse_script(data, codec='cp932'):
    """Return commands covering every byte; reject unknown opcodes and short operands."""
    return frame.parse_commands(data, NAMES, FORMATS, SPECIAL, codec)


def text_arguments(command):
    """Return the string argument records that carry displayable text."""
    if command['opcode'] in (BUNSYOU, BUNSYOU_RUBI):
        return [record for record in command['args'] if record['type'] == 's']
    return []


def parse_bin(raw, codec='cp932'):
    """Parse a complete scenario image; validate labels against command boundaries.

    Unlike 20050817 there is no ``FFFF`` envelope, no declared size and no ZIP:
    the image starts directly with its version tag.
    """
    labels, script, start = frame.split_script(raw, VERSION)
    commands = parse_script(script, codec)
    frame.validate_labels(labels, commands, len(script))
    return dict(version=raw[:8], script_offset=start, labels=labels, commands=commands,
                script_size=len(script))


def parse_index(raw):
    """Validate the scn0.bin index envelope, which carries no label table or script."""
    if len(raw) < 11 or raw[:8] != INDEX_VERSION:
        raise ValueError('Unsupported scenario index version')
    count = int.from_bytes(raw[8:11], 'little')
    if count != 0 or len(raw) != 11:
        raise ValueError('Unidentified scenario index layout')
    return dict(version=raw[:8], entries=count)
