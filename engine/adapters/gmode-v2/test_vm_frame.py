import struct
import unittest
from vm_frame import (Reader, decode_text, offset_table, parse_commands, split_script,
                      validate_labels)

NAMES = {1: 'TOBU', 2: 'SABU', 24: 'MOJI_ON'}
FORMATS = {1: 'h', 2: 'h'}


def moji_on(reader, command, read):
    if read('B'):
        read('s')


SPECIAL = {24: moji_on}


def text_table():
    """A 65537-entry uint16 table; entries default to their own code point."""
    table = list(range(65537))
    table[0x8140] = 0x4E00
    return tuple(table)


class DecodeTests(unittest.TestCase):
    def test_single_byte_codes_match_the_python_codec(self):
        self.assertEqual(decode_text(b'AB', 'cp932'), decode_text(b'AB', text_table()))

    def test_original_table_merges_lead_and_trail_bytes(self):
        self.assertEqual(decode_text(bytes([0x81, 0x40]), text_table()), '一')
        self.assertEqual(decode_text(bytes([0x81, 0x40]), 'cp932'), '　')

    def test_rejects_wrong_table_size(self):
        with self.assertRaises(ValueError):
            decode_text(b'A', (0,) * 10)

    def test_rejects_truncated_original_codec_lead(self):
        with self.assertRaisesRegex(ValueError, 'lead byte'):
            decode_text(bytes([0x81]), text_table())


class ReaderTests(unittest.TestCase):
    def test_numbers_are_big_endian(self):
        self.assertEqual(Reader(bytes([0x12, 0x34])).number('h'), 0x1234)
        self.assertEqual(Reader(bytes([0xFF, 0xFE])).number('h'), -2)
        self.assertEqual(Reader(bytes([0xFF, 0xFE])).number('H'), 0xFFFE)

    def test_string_consumes_its_terminator(self):
        reader = Reader(b'ab\0c')
        self.assertEqual(reader.string(), 'ab')
        self.assertEqual(reader.pos, 3)

    def test_string_stops_at_the_local_buffer_limit(self):
        reader = Reader(b'a' * 100 + b'\0')
        self.assertEqual(reader.string(), 'a' * 100)
        self.assertEqual(reader.pos, 101)

    def test_string_rejects_unterminated_tail(self):
        with self.assertRaisesRegex(ValueError, 'Unterminated StringRead'):
            Reader(b'abc').string()

    def test_arg_records_offsets(self):
        record = Reader(b'ab\0').arg('s')
        self.assertEqual((record['offset'], record['end'], record['type'], record['value']), (0, 3, 's', 'ab'))

    def test_take_rejects_short_reads(self):
        with self.assertRaisesRegex(ValueError, 'Truncated operand'):
            Reader(b'a').take(2)


class CommandTests(unittest.TestCase):
    def test_fixed_layout_and_specials(self):
        commands = parse_commands(bytes([1, 0x12, 0x34, 24, 1]) + b'snd\0', NAMES, FORMATS, SPECIAL)
        self.assertEqual([command['name'] for command in commands], ['TOBU', 'MOJI_ON'])
        self.assertEqual(commands[0]['args'][0]['value'], 0x1234)
        self.assertEqual([record['value'] for record in commands[1]['args']], [1, 'snd'])
        self.assertEqual(commands[-1]['end'], 9)

    def test_with_rows_is_opt_in(self):
        plain = parse_commands(bytes([1, 0, 0]), NAMES, FORMATS)
        with_rows = parse_commands(bytes([1, 0, 0]), NAMES, FORMATS, with_rows=True)
        self.assertNotIn('rows', plain[0])
        self.assertEqual(with_rows[0]['rows'], [])

    def test_rejects_unknown_opcode_and_missing_layout(self):
        with self.assertRaisesRegex(ValueError, 'Unknown opcode'):
            parse_commands(bytes([9, 0]), NAMES, FORMATS)
        with self.assertRaisesRegex(ValueError, 'No operand layout'):
            parse_commands(bytes([2, 0, 0]), NAMES, {})


class LabelTests(unittest.TestCase):
    def test_split_script_reads_the_label_table(self):
        payload = b'20050117' + bytes(3) + struct.pack('<H', 2) + struct.pack('<HH', 0, 3) + bytes([1, 0, 0])
        labels, script, offset = split_script(payload, b'20050117')
        self.assertEqual(labels, [0, 3])
        self.assertEqual(script, bytes([1, 0, 0]))
        self.assertEqual(offset, 17)

    def test_split_script_rejects_version_and_truncation(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported scenario version'):
            split_script(b'20050817' + bytes(20), b'20050117')
        with self.assertRaisesRegex(ValueError, 'Invalid scenario envelope'):
            split_script(b'2005', b'2005')
        with self.assertRaisesRegex(ValueError, 'Truncated label table'):
            split_script(b'20050117' + bytes(3) + struct.pack('<H', 9), b'20050117')

    def test_validate_labels_rejects_operand_interiors(self):
        commands = parse_commands(bytes([1, 0, 0]), NAMES, FORMATS)
        validate_labels([0, 3], commands, 3)
        with self.assertRaisesRegex(ValueError, 'Labels inside operands'):
            validate_labels([1], commands, 3)


def container(members, count_size=1):
    table = b''
    offset = 0
    for name, payload in members:
        table += name + b'\0' + struct.pack('>HH', offset % 65536, len(payload))
        offset += len(payload)
    return len(members).to_bytes(count_size, 'big') + table + b''.join(payload for _, payload in members)


class OffsetTableTests(unittest.TestCase):
    def test_one_and_two_byte_counts(self):
        members = ((b'a.bin', b'xyz'), (b'b.gif', b'q'))
        expected = [('a.bin', b'xyz'), ('b.gif', b'q')]
        for count_size in (1, 2):
            with self.subTest(count_size=count_size):
                self.assertEqual(offset_table(container(members, count_size), count_size), expected)

    def test_rejects_corrupt_containers(self):
        good = container(((b'a.bin', b'xyz'),))
        cases = {'empty': b'', 'truncated': good[:-1], 'trailing': good + b'\0',
                 'duplicate': container(((b'a.bin', b'x'), (b'a.bin', b'y'))),
                 'path': container(((b'd/a.bin', b'x'),))}
        for label, data in cases.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                offset_table(data, 1)


if __name__ == '__main__':
    unittest.main()
