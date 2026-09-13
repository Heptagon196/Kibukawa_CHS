"""Validate native source metrics/pixels, UI coverage and packed atlas."""
import unittest
import build_pixel_font as font
from zlabs_font import load_source

class NativePixelTests(unittest.TestCase):
    def test_source_metrics_and_pixels(self):
        glyphs,_=font.load_ui_glyphs()
        for cp,g in load_source()[1].characters.items():
            advance,w,h,x,y,rows=glyphs[cp]
            self.assertEqual((advance,w,h,x,y),(g.advance,g.width,g.height,g.x,g.y-g.height))
            for yy,row in enumerate(g.bitmap):
                for xx,value in enumerate(row):
                    self.assertEqual(bool(rows[yy] & (1<<(w-xx-1))),bool(value))
    def test_actual_small_ui_has_no_missing_characters(self):
        glyphs,_=font.load_ui_glyphs()
        chars,_,_=font.collect_characters(ui_only=True)
        self.assertFalse(set(chars)-set(glyphs))
        self.assertTrue(set(map(ord,'白鹭洲伊纲'))<=set(glyphs))
        # Dialogue uses Unifont 16px; do not require its uncommon characters
        # in the separate Z Labs 12px UI font. Validate both actual atlases.
    def test_built_atlas_preserves_native_pixels(self):
        report=font.build_font(font.ROOT/'build/font-test')
        self.assertFalse(report['missingGlyphs'])
        self.assertEqual(report['glyphCount'],report['requiredGlyphs'])
        self.assertFalse(report['uiFont']['missingGlyphs'])
        self.assertTrue(report['uiFont']['validation']['native_pixels_preserved'])
        self.assertFalse(report['uiFont']['resampled'])
    def test_icons_fit_twelve_pixel_label_band(self):
        import zipfile
        lock=font.load(font.ROOT/'fusion-icon-font-dependency.lock.json')
        with zipfile.ZipFile(font.dependency(lock['dependencies']['bdf'])) as z:
            glyphs=font.parse_bdf(z.read('fusion-pixel-10px-monospaced-zh_hans.bdf'),(5,10))
        for c in '交谈调查移动呼叫出示思考环视电脑存档笔记':
            a,w,h,x,y,rows=glyphs[ord(c)]
            self.assertEqual(a,10)
            self.assertTrue(0<=2+x and 2+x+w<=12 and 12<=22-(y+h) and 22-y<=24)
if __name__=='__main__':unittest.main()
