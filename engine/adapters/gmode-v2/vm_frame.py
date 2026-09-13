"""Version-neutral command frame shared by the G-MODE script VMs.

The eighth title (``20050817``) and the ninth title (``20050117``) decode their
scenario scripts the same way:

* a script region is a flat byte stream of ``opcode`` + operands, with no
  alignment or padding;
* the label table that precedes the script is identical in both versions
  (16-bit little-endian count at byte 11, little-endian label table from byte
  13, script immediately after it);
* numbers are signed or unsigned 16-bit big-endian;
* strings are NUL-terminated Shift-JIS read through a 100-byte local buffer.

What differs is the envelope around the script, the opcode tables, and a
handful of handlers whose operands are conditional. Those stay in each adapter;
everything above lives here so the frame is written once.

Importing: consumers put this directory on ``sys.path`` and import by name, the
same way the works' scripts pull in ``engine/tools``. See README.md.
"""
import struct

CHUNK = 65536
STRING_LIMIT = 100


def decode_text(data, codec='cp932'):
    """Decode with a Python codec name or the original 65537-entry uint16 table."""
    if isinstance(codec, str):
        return data.decode(codec)
    if len(codec) != 65537:
        raise ValueError('Original codec table must have 65537 entries')
    out = []
    pos = 0
    while pos < len(data):
        code = data[pos]
        pos += 1
        if 0x81 <= code <= 0x9f or 0xe0 <= code <= 0xea:
            if pos == len(data):
                raise ValueError('Truncated original-codec lead byte')
            code = code * 256 + data[pos]
            pos += 1
        out.append(chr(codec[code]))
    return ''.join(out)


class Reader:
    """Byte cursor over a script region with the original operand primitives."""

    def __init__(self, data, codec='cp932'):
        self.data = data
        self.codec = codec
        self.pos = 0

    def take(self, n):
        if n < 0 or self.pos + n > len(self.data):
            raise ValueError(f'Truncated operand at {self.pos:#x}: need {n} bytes')
        value = self.data[self.pos:self.pos + n]
        self.pos += n
        return value

    def number(self, kind='B'):
        return struct.unpack('>' + kind, self.take(struct.calcsize(kind)))[0]

    def string(self):
        """Mirror the original StringRead, including its unconditional terminator skip.

        The original copies at most ``STRING_LIMIT`` bytes into a local buffer and
        stops at a NUL, then always advances the cursor by one more byte. When no
        NUL appears within the limit the string is the full buffer and the extra
        byte is skipped; both shipped corpora contain no such string, so this is
        indistinguishable from a stricter "unterminated" rejection on real data.
        """
        start = self.pos
        end = self.data.find(b'\0', self.pos, min(len(self.data), self.pos + STRING_LIMIT + 1))
        if end < 0:
            if len(self.data) - self.pos < STRING_LIMIT:
                raise ValueError(f'Unterminated StringRead at {start:#x}')
            end = self.pos + STRING_LIMIT
        value = decode_text(self.data[self.pos:end], self.codec)
        self.pos = end + 1
        return value

    def arg(self, kind):
        start = self.pos
        value = self.string() if kind == 's' else self.number(kind)
        return dict(offset=start, end=self.pos, type=kind, value=value)


def parse_commands(data, names, formats, special=None, codec='cp932', with_rows=False):
    """Decode a script region into commands covering every byte.

    ``names`` maps opcode to mnemonic. ``formats`` maps opcode to a fixed operand
    layout string (``''`` for no operands). ``special`` maps an opcode to a
    ``handler(reader, command, read)`` used when the operands are conditional;
    it takes precedence over ``formats``. Unknown opcodes and short operands are
    rejected rather than skipped.

    ``with_rows`` initialises an empty ``rows`` list on every command. The 20050817
    version always exposes that key because its text commands fill it with
    colour/control/ruby planes; 20050117 has no row model and omits it.
    """
    reader = Reader(bytes(data), codec)
    handlers = special or {}
    commands = []
    while reader.pos < len(reader.data):
        start = reader.pos
        opcode = reader.number()
        if opcode not in names:
            raise ValueError(f'Unknown opcode {opcode:#x} at {start:#x}')
        command = dict(offset=start, opcode=opcode, name=names[opcode], args=[])
        if with_rows:
            command['rows'] = []

        def read(kind):
            record = reader.arg(kind)
            command['args'].append(record)
            return record['value']

        if opcode in handlers:
            handlers[opcode](reader, command, read)
        else:
            layout = formats.get(opcode)
            if layout is None:
                raise ValueError(f'No operand layout for opcode {opcode:#x} at {start:#x}')
            for kind in layout:
                read(kind)
        command['end'] = reader.pos
        commands.append(command)
    return commands


def split_script(payload, version):
    """Validate the version tag and label table; return ``(labels, script, offset)``.

    ``payload`` starts at the version tag. The three reserved bytes at 8..11 and
    the 16-bit little-endian label count at 11..13 are identical across the
    versions that share this frame; callers strip their own envelope first.
    """
    if len(payload) < 13:
        raise ValueError('Invalid scenario envelope')
    if payload[:8] != version:
        raise ValueError('Unsupported scenario version ' + repr(payload[:8]))
    count = int.from_bytes(payload[11:13], 'little')
    start = 13 + 2 * count
    if start > len(payload):
        raise ValueError('Truncated label table')
    labels = list(struct.unpack_from('<' + 'H' * count, payload, 13))
    return labels, payload[start:], start


def validate_labels(labels, commands, script_size):
    """Reject labels that point inside an operand rather than at a command start."""
    boundaries = {command['offset'] for command in commands} | {script_size}
    invalid = [label for label in labels if label not in boundaries]
    if invalid:
        raise ValueError(f'Labels inside operands: {invalid}')


def offset_table(data, count_size):
    """Split a scratch container into ordered ``(name, payload)`` pairs.

    Layout: a big-endian member count of ``count_size`` bytes, that many
    NUL-terminated ASCII names each followed by a big-endian ``(offset, length)``
    pair, then the packed payloads. Offsets are payload-relative modulo one
    64 KiB chunk. The eighth title uses a two-byte count for its image
    containers; the ninth title uses a one-byte count for its combined
    scenario/image container.
    """
    if not data or len(data) < count_size + 1:
        raise ValueError('Empty scratch container')
    count = int.from_bytes(data[:count_size], 'big')
    cursor = count_size
    records = []
    names = set()
    for _ in range(count):
        end = data.index(0, cursor)
        name = data[cursor:end].decode('ascii')
        if not name or '/' in name or '\\' in name or name in names:
            raise ValueError('Invalid scratch member name')
        names.add(name)
        cursor = end + 1
        offset, length = struct.unpack_from('>HH', data, cursor)
        cursor += 4
        records.append((name, offset, length))
    base = cursor
    result = []
    for name, offset, length in records:
        if offset != (cursor - base) % CHUNK:
            raise ValueError('Unexpected packed offset')
        if cursor + length > len(data):
            raise ValueError('Truncated scratch member')
        result.append((name, data[cursor:cursor + length]))
        cursor += length
    if cursor != len(data):
        raise ValueError('Trailing container data')
    return result
