import struct
import unittest
from kbf3_atlas import encode_kbf3


class Kbf3Tests(unittest.TestCase):
    def test_metrics_alpha_and_placement(self):
        index, rgba = encode_kbf3(12, 4, 4, [(65, 1, 1, 6, 2, 2, -1, -3, bytes([255, 0, 128, 1]))])
        self.assertEqual(struct.unpack('<5i', index[:20]), (0x3346424b, 12, 4, 4, 1))
        self.assertEqual(struct.unpack('<8i', index[20:]), (65, 1, 1, 6, 2, 2, -1, -3))
        self.assertEqual(rgba[20:28], bytes([255,255,255,255,0,0,0,0]))
        self.assertEqual(rgba[36:44], bytes([255,255,255,128,255,255,255,1]))

    def test_transparent_rgb_and_empty_glyph(self):
        index, rgba = encode_kbf3(12, 2, 2, [(32,0,0,6,0,0,0,0,b''), (65,1,1,6,1,1,0,-1,b'\0')], transparent_white=True)
        self.assertEqual(rgba[-4:], b'\xff\xff\xff\0')
        self.assertEqual(len(index), 84)

    def test_reject_invalid_records(self):
        valid = (65,0,0,6,1,1,0,-1,b'\xff')
        for glyphs in [[valid,valid], [(65,2,0,6,1,1,0,0,b'\xff')], [(65,0,0,6,2,1,0,0,b'')]]:
            with self.assertRaises(ValueError): encode_kbf3(12,2,2,glyphs)


if __name__ == '__main__': unittest.main()
