"""Verify real VM context for the one paragraph requiring the fifth narrator row."""
import unittest
import pipeline as p
from runtime_pack import codec_for

class ContextTests(unittest.TestCase):
    def test_narrator_has_five_rows_without_crossing_a_branch_or_label(self):
        parsed=p.parse_bin((p.WORK/'raw/scratch4.dat/s01.bin').read_bytes(),codec_for(p.WORK))
        target=21531
        prior=[c for c in parsed['commands'] if c['offset']<target]
        name=next(c for c in reversed(prior) if c['name']=='NAMAE')
        self.assertEqual(name['args'][0]['value'],-1)
        self.assertFalse(any(name['offset']<label<=target for label in parsed['labels']))
        self.assertTrue(all(c['name']=='BUNSYOU' for c in prior if c['offset']>name['offset']))

if __name__=='__main__':unittest.main()
