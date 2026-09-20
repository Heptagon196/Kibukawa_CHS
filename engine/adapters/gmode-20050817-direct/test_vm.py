"""Offline operand and shipped-corpus checks; never launch the game."""
import base64
import json
from pathlib import Path
import struct
import unittest
import vm

PROJECT = Path(__file__).resolve().parents[3] / 'games/10-kibu10'


class VariantTests(unittest.TestCase):
    def test_operand_differences(self):
        # KOMANDO(short), background(flag, optional string), subtitle(byte,string), selector.
        raw = b'20050817' + bytes(5) + bytes([5, 255, 255, 40, 1]) + b'bg\0' + bytes([73, 2]) + b'title\0' + bytes([76])
        commands = vm.parse_bin(raw)['commands']
        self.assertEqual([c['opcode'] for c in commands], [5, 40, 73, 76])
        self.assertEqual(commands[0]['args'][0]['value'], -1)
        self.assertEqual(commands[2]['args'][1]['value'], 'title')
        self.assertIn(5, vm.base.SPECIAL)  # importing variant must not change eighth-game tables

    def test_unknown_and_truncated_rejected(self):
        for script in (b'\x83', b'\x49\x01title', b'\x05\xff'):
            with self.assertRaises(ValueError):
                vm.parse_bin(b'20050817' + bytes(5) + script)

    def test_original_corpus(self):
        assembly = json.loads((PROJECT / 'research/kibu10-assembly.json').read_text('utf8'))
        codec = struct.unpack('<65537H', base64.b64decode(assembly['codec_base64']))
        paths = list((PROJECT / 'raw').rglob('*.bin'))
        self.assertEqual(len(paths), 40)
        total = 0
        for path in paths:
            parsed = vm.parse_bin(path.read_bytes(), codec)
            commands = parsed['commands']
            self.assertEqual(commands[-1]['end'], parsed['script_size'])
            total += len(commands)
        self.assertEqual(total, 19834)


if __name__ == '__main__':
    unittest.main()
