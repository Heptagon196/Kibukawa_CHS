"""Transactional installation tests in disposable directories; never target a game."""
import json
from pathlib import Path
import uuid
import shutil
import unittest
from unittest.mock import patch
import install_patch as installer


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.test_parent = Path(__file__).resolve().parents[1]/'build/installer-tests'
        self.root = self.test_parent/uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.work = self.root/'work'
        self.game = self.root/'GmodeArchivesPlus_kibu8'
        self.game.mkdir()
        (self.game/'kibu8.exe').write_bytes(b'original fixture')
        self.relative = 'BepInEx/plugins/Kibu8ZhCN/Kibu8ZhCN.dll'
        old = self.game/self.relative
        old.parent.mkdir(parents=True)
        old.write_bytes(b'previous fixture plugin')
        package = self.work/'out/release/package'
        (package/self.relative).parent.mkdir(parents=True)
        (package/self.relative).write_bytes(b'new fixture plugin')
        (package/'README_Kibu8_CHS.txt').write_bytes(b'new fixture readme')
        installer.save(self.work/'work/manifest.json', {'game_hashes':{'kibu8.exe':installer.sha(self.game/'kibu8.exe')}})
        installer.save(self.work/'reports/build_latest.json', dict(version='test',output='out/release',
            package_files={p.relative_to(package).as_posix():installer.sha(p) for p in package.rglob('*') if p.is_file()}))
        self.patches = [patch.object(installer,'WORK',self.work),patch.object(installer,'GAME',self.game),patch.object(installer,'game_closed',lambda:None)]
        for item in self.patches: item.start()
    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        self.assertTrue(self.root.resolve().is_relative_to(self.test_parent.resolve()))
        shutil.rmtree(self.root)
    def test_install_restore_exact_previous_bytes(self):
        installer.install()
        record = installer.load(self.work/'reports/installation_latest.json')
        self.assertEqual((self.game/self.relative).read_bytes(),b'new fixture plugin')
        installer.restore(Path(record['manifest']))
        self.assertEqual((self.game/self.relative).read_bytes(),b'previous fixture plugin')
        self.assertFalse((self.game/'README_Kibu8_CHS.txt').exists())
        self.assertEqual((self.game/'kibu8.exe').read_bytes(),b'original fixture')
    def test_copy_failure_rolls_back(self):
        original_copy = installer.copy_atomic
        def fail_readme(source,target):
            if source.name=='README_Kibu8_CHS.txt': raise OSError('injected copy failure')
            original_copy(source,target)
        with patch.object(installer,'copy_atomic',fail_readme):
            with self.assertRaises(OSError): installer.install()
        self.assertEqual((self.game/self.relative).read_bytes(),b'previous fixture plugin')
        self.assertFalse((self.game/'README_Kibu8_CHS.txt').exists())
    def test_tampered_package_rejected_before_writes(self):
        (self.work/'out/release/package'/self.relative).write_bytes(b'tampered')
        with self.assertRaises(ValueError): installer.install()
        self.assertEqual((self.game/self.relative).read_bytes(),b'previous fixture plugin')


if __name__=='__main__': unittest.main()
