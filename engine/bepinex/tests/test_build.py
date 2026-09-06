"""Shared infrastructure regression tests; network responses are mocked."""
import io
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'engine/bepinex'))
import build

class SharedBuildTests(unittest.TestCase):
    def setUp(self):
        self.lock_path=ROOT/'engine/bepinex/locks/BepInEx-5.4.23.5-win-x64.json'
        self.lock=build.load(self.lock_path)
        self.archive=(ROOT/'cache/bepinex/mono-win-x64-5.4.23.5'/self.lock['asset']).read_bytes()
        self.assertEqual(build.sha(self.archive),self.lock['sha256'])
        self.root=ROOT/'cache/bepinex-tests'/uuid.uuid4().hex
        self.root.mkdir(parents=True)

    def cached(self):
        path=self.root/self.lock['asset']; path.write_bytes(self.archive); return path

    def ensure(self,refresh=False):
        return build.ensure_framework(self.lock_path,self.root,refresh)

    def test_missing_download(self):
        with patch.object(build.urllib.request,'urlopen',return_value=io.BytesIO(self.archive)) as network:
            path,report=self.ensure()
        self.assertTrue(report['downloaded'])
        self.assertTrue((path/'winhttp.dll').is_file())
        self.assertEqual(network.call_args.args[0].full_url,self.lock['url'])

    def test_offline_shared_cache_repairs_extraction(self):
        self.cached()
        with patch.object(build.urllib.request,'urlopen',side_effect=AssertionError('No network expected')):
            first,_=self.ensure()
            file=first/'winhttp.dll'; original=file.read_bytes(); file.write_bytes(b'bad')
            second,report=self.ensure()
        self.assertEqual(first,second)
        self.assertEqual(file.read_bytes(),original)
        self.assertFalse(report['downloaded'])

    def test_corrupt_cache_redownloads(self):
        path=self.cached(); path.write_bytes(b'bad')
        with patch.object(build.urllib.request,'urlopen',return_value=io.BytesIO(self.archive)):
            _,report=self.ensure()
        self.assertTrue(report['downloaded']); self.assertEqual(path.read_bytes(),self.archive)

    def test_bad_download_preserves_good_cache(self):
        path=self.cached()
        with patch.object(build.urllib.request,'urlopen',return_value=io.BytesIO(b'bad')):
            with self.assertRaisesRegex(ValueError,'hash mismatch'): self.ensure(True)
        self.assertEqual(path.read_bytes(),self.archive)
        self.assertFalse(path.with_suffix('.download').exists())

    def test_package_rejects_original_and_escape(self):
        file=self.root/'payload.txt'; file.write_text('test')
        for payload,forbidden in [({'../outside.txt':file},set()),({'game.dat':file},{'game.dat'})]:
            with self.assertRaises(ValueError):
                build.stage_package(self.root/'package',self.root,{'files':[]},payload,forbidden)
        self.assertFalse((self.root/'package').exists())

    def test_distinct_cache_roots(self):
        with patch.object(build.urllib.request,'urlopen',side_effect=lambda *a,**kw:io.BytesIO(self.archive)):
            first,_=self.ensure()
            second,_=build.ensure_framework(self.lock_path,self.root/'other-profile')
        self.assertNotEqual(first,second)
        self.assertEqual((first/'winhttp.dll').read_bytes(),(second/'winhttp.dll').read_bytes())

if __name__=='__main__': unittest.main(verbosity=2)
