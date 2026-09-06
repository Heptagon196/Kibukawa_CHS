"""Exercise dependency recovery without contacting the network or touching game files."""
import io
from pathlib import Path
import sys
import uuid
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import build_bepinex as build


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.original_root = build.ROOT
        self.lock = build.p.load(build.ROOT / 'dependency.lock.json')
        self.official_zip = (build.ROOT / 'deps' / self.lock['asset']).read_bytes()
        build.p.require(build.p.sha(self.official_zip) == self.lock['sha256'], 'Test requires verified dependency cache')
        # Regular mkdir inherits the workspace ACL; Windows Python 3.14 temp dirs
        # use restrictive ACLs that prevent access by some sandbox identities.
        test_root = build.p.inside(build.ROOT / 'build/dependency_tests' / uuid.uuid4().hex)
        test_root.mkdir(parents=True)
        self.addCleanup(setattr, build, 'ROOT', self.original_root)
        build.ROOT = test_root
        build.p.save(build.ROOT / 'dependency.lock.json', self.lock)

    def cached_zip(self, data):
        path = build.ROOT / 'deps' / self.lock['asset']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_missing_archive_downloads_verified_framework(self):
        with patch.object(build.urllib.request, 'urlopen', return_value=io.BytesIO(self.official_zip)) as network:
            root, report = build.ensure_framework()
        self.assertTrue(report['downloaded'])
        self.assertTrue((root / 'winhttp.dll').is_file())
        self.assertEqual(network.call_args.args[0].full_url, self.lock['url'])

    def test_verified_cache_is_offline_and_repairs_extracted_files(self):
        self.cached_zip(self.official_zip)
        with patch.object(build.urllib.request, 'urlopen', side_effect=AssertionError('Cache must work offline')):
            root, _ = build.ensure_framework()
            loader = root / 'winhttp.dll'
            expected = loader.read_bytes()
            loader.write_bytes(b'corrupted extraction')
            _, report = build.ensure_framework()
        self.assertFalse(report['downloaded'])
        self.assertEqual(loader.read_bytes(), expected)

    def test_corrupt_cache_is_downloaded_again(self):
        archive = self.cached_zip(b'bad cache')
        with patch.object(build.urllib.request, 'urlopen', return_value=io.BytesIO(self.official_zip)):
            _, report = build.ensure_framework()
        self.assertTrue(report['downloaded'])
        self.assertEqual(archive.read_bytes(), self.official_zip)

    def test_bad_download_is_rejected_without_replacing_verified_cache(self):
        archive = self.cached_zip(self.official_zip)
        with patch.object(build.urllib.request, 'urlopen', return_value=io.BytesIO(b'bad download')):
            with self.assertRaisesRegex(Exception, 'hash mismatch'):
                build.ensure_framework(refresh=True)
        self.assertEqual(archive.read_bytes(), self.official_zip)
        self.assertFalse(archive.with_suffix('.download').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
