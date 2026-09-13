"""Offline invariants against shipped scripts and malformed operand fixtures."""
import base64
import json
import struct
import pathlib
import unittest
from vm import parse_bin, parse_script, decode_text

ROOT=pathlib.Path(__file__).resolve().parents[3]

class VmTests(unittest.TestCase):
    def test_originals_complete_and_labels_aligned(self):
        files=list((ROOT/'games/08-kibu8/raw').rglob('*.bin'))
        self.assertEqual(len(files),59)
        for path in files:
            with self.subTest(path=str(path)):
                parsed=parse_bin(path.read_bytes())
                cursor=0
                for command in parsed['commands']:
                    self.assertEqual(command['offset'],cursor)
                    self.assertGreater(command['end'],cursor)
                    cursor=command['end']
                    for row in command['rows']:
                        self.assertEqual(''.join(row['cells']),row['text'])
                        self.assertEqual(len(row['colors']),row['cells_count'])
                        if command['opcode']==255:
                            self.assertEqual(len(row['controls']),row['cells_count'])
                            self.assertEqual(len(row['ruby_indices']),row['cells_count'])
                self.assertEqual(cursor,parsed['script_size'])
    def test_original_codec_matches_corpus_and_preserves_special_bytes(self):
        assembly=json.loads((ROOT/'games/08-kibu8/research/kibu8-assembly.json').read_text())
        table=struct.unpack('<65537H',base64.b64decode(assembly['codec_base64']))
        self.assertEqual(decode_text(bytes([255,255]),table),chr(0)*2)
        for path in (ROOT/'games/08-kibu8/raw').rglob('*.bin'):
            with self.subTest(path=str(path)):
                raw=path.read_bytes()
                self.assertEqual(parse_bin(raw,table),parse_bin(raw))
    def test_big_endian_operands(self):
        c=parse_script(bytes([1,0x12,0x34,47,255]))
        self.assertEqual(c[0]['args'][0]['value'],0x1234)
        self.assertEqual(c[1]['args'][0]['value'],-1)
    def test_row_planes_and_ruby_glyphs(self):
        # Two slots: fullwidth glyph then a halfwidth pair; colon precedes second slot.
        raw=bytes([255,1,2,2])+'名AB'.encode('cp932')+bytes([255,0,2,3,0,58,1,1,1,240,0])
        row=parse_script(raw)[0]['rows'][0]
        self.assertEqual(row['cells'],['名','AB'])
        self.assertEqual(row['ruby_indices'],[-1,0])
        self.assertEqual(row['colors'],[2,3])
        self.assertEqual(row['events'][0]['name'],'colon')
        self.assertEqual(row['rubies'][0]['bytes'],[240,0])
    def test_rejects_truncation_unknown_and_unterminated(self):
        for data in [b'\x01\x00',b'\x00',b'\x50abc',b'\xff\x01\x01\x01']:
            with self.subTest(data=data),self.assertRaises(ValueError): parse_script(data)
    def test_rejects_label_inside_operand(self):
        payload=b'20050817'+bytes(3)+b'\x01\x00'+b'\x01\x00'+b'\x01\x00\x00'
        raw=b'\xff\xff'+len(payload).to_bytes(2,'little')+payload
        with self.assertRaisesRegex(ValueError,'Labels inside operands'): parse_bin(raw)

if __name__=='__main__': unittest.main()
