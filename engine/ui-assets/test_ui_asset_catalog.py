import unittest
import json
from ui_asset_catalog import ROOT, resolve_asset, validate_source


class SharedArtworkTests(unittest.TestCase):
    def test_all_assets_and_original_fingerprints(self):
        assets=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))['assets']
        self.assertEqual(len(assets),15)
        for key in assets:
            _,entry=resolve_asset(key)
            if entry.get('kind')=='build-template':
                with self.assertRaises(ValueError):validate_source(entry,{})
                continue
            source=dict(size=entry['size'],source_rgba_sha256=entry['source_rgba_sha256'][0])
            validate_source(entry,source)
            with self.assertRaises(ValueError):validate_source(entry,dict(source,source_rgba_sha256='0'*64))
            with self.assertRaises(ValueError):validate_source(entry,dict(source,size=[1,1]))

    def test_no_filename_fallback(self):
        with self.assertRaises(KeyError):resolve_asset('cmd0.gif')


if __name__=='__main__':unittest.main()
