"""Offline invariants against the shipped ninth-title scripts and malformed fixtures."""
import base64
import json
import pathlib
import struct
import unittest
from vm import NAMES, decode_text, parse_bin, parse_index, parse_script, text_arguments

ROOT = pathlib.Path(__file__).resolve().parents[3]
RAW = ROOT / 'games/09-samidare/raw'
ASSEMBLY = ROOT / 'games/09-samidare/research/kibu9-assembly.json'


def scenario_files():
    return sorted(path for path in RAW.rglob('*.bin') if path.name != 'scn0.bin')


class VmTests(unittest.TestCase):
    def test_originals_complete_and_labels_aligned(self):
        files = scenario_files()
        self.assertEqual(len(files), 14)
        for path in files:
            with self.subTest(path=path.name):
                parsed = parse_bin(path.read_bytes())
                cursor = 0
                for command in parsed['commands']:
                    self.assertEqual(command['offset'], cursor)
                    self.assertGreater(command['end'], cursor)
                    cursor = command['end']
                    for record in command['args']:
                        self.assertGreater(record['end'], record['offset'])
                self.assertEqual(cursor, parsed['script_size'])

    def test_index_envelope(self):
        raw = (RAW / 'scratchpad/scn0.bin').read_bytes()
        self.assertEqual(parse_index(raw)['version'], b'20050524')

    def test_original_codec_matches_corpus(self):
        assembly = json.loads(ASSEMBLY.read_text(encoding='utf-8-sig'))
        table = struct.unpack('<65537H', base64.b64decode(assembly['codec_base64']))
        self.assertEqual(decode_text(bytes([255, 255]), table), chr(0) * 2)
        for path in scenario_files():
            with self.subTest(path=path.name):
                raw = path.read_bytes()
                self.assertEqual(parse_bin(raw, table), parse_bin(raw))

    def test_big_endian_operands_and_string_limit(self):
        commands = parse_script(bytes([1, 0x12, 0x34, 47, 255]))
        self.assertEqual(commands[0]['args'][0]['value'], 0x1234)
        self.assertEqual(commands[1]['args'][0]['value'], -1)
        long_text = bytes([255, 0, 0, 0]) + b'a' * 100 + b'\0'
        self.assertEqual(parse_script(long_text)[0]['args'][3]['value'], 'a' * 100)

    def test_bunsyou_carries_three_setup_bytes_and_one_string(self):
        text = '名AB'.encode('cp932')
        raw = bytes([255, 8, 3, 3]) + text + b'\0'
        command = parse_script(raw)[0]
        self.assertEqual(NAMES[255], 'BUNSYOU')
        self.assertEqual([record['value'] for record in command['args'][:3]], [8, 3, 3])
        self.assertEqual(text_arguments(command)[0]['value'], '名AB')

    def test_conditional_operands(self):
        self.assertEqual(len(parse_script(bytes([24, 0]))[0]['args']), 1)
        self.assertEqual(len(parse_script(bytes([24, 1]) + b'se_mes00\0')[0]['args']), 2)
        self.assertEqual(len(parse_script(bytes([40, 0]))[0]['args']), 1)
        self.assertEqual(len(parse_script(bytes([40, 1]) + b'bg00.jpg\0')[0]['args']), 2)

    def test_rejects_truncation_unknown_and_unterminated(self):
        for data in [b'\x01\x00', b'\x00', b'\x50abc', b'\xff\x01\x01', bytes([24, 1]) + b'abc']:
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_script(data)

    def test_rejects_label_inside_operand_and_wrong_version(self):
        payload = b'20050117' + bytes(3) + struct.pack('<H', 1) + struct.pack('<H', 1) + bytes([1, 0, 0])
        with self.assertRaisesRegex(ValueError, 'Labels inside operands'):
            parse_bin(payload)
        with self.assertRaisesRegex(ValueError, 'Unsupported scenario version'):
            parse_bin(b'20050817' + payload[8:])


if __name__ == '__main__':
    unittest.main()
