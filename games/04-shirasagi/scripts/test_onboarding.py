"""Offline checks for fourth-game resource routing and release gating."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import pipeline as p


class Onboarding(unittest.TestCase):
    def test_relative_path_and_release_gate(self):
        self.assertEqual(p.PROJECT['installation'], p.SERIES.parent.parent/'GmodeArchivesPlus_kibu4')
        self.assertTrue(p.resolve('kibu4')['enabled'])
        self.assertFalse(p.load(p.WORK/'project.json')['compatibility']['runtime_tested'])

    def test_both_archive_halves_are_extracted(self):
        manifest = p.validate_sources()
        expected = {'sirasagi-1.res': set(range(4)), 'sirasagi-2.res': set(range(4, 8))}
        for archive, numbers in expected.items():
            actual = {int(e['location']['member'][3:]) for e in manifest['entries']
                      if e['location'].get('asset') == archive}
            self.assertEqual(actual, numbers)

    def test_duplicate_assets_must_match(self):
        def obj(value):
            return SimpleNamespace(type=SimpleNamespace(name='TextAsset'),
                read=lambda: SimpleNamespace(m_Name='define', m_Script=value))
        with patch.object(p.UnityPy, 'load', return_value=SimpleNamespace(objects=[obj('a'), obj('a')])):
            self.assertEqual(p.text_assets('unused'), {'define': b'a'})
        with patch.object(p.UnityPy, 'load', return_value=SimpleNamespace(objects=[obj('a'), obj('b')])):
            with self.assertRaisesRegex(ValueError, 'Conflicting TextAsset'):
                p.text_assets('unused')

    def test_previous_translations_unchanged(self):
        # Other tasks may legitimately update prior runtime code/build artifacts.
        # Never reset that work to the historical onboarding baseline.
        # Each build separately compares complete prior directories before/after.
        baseline = p.load(p.WORK/'reports/previous-projects-start.json')
        current = p.first_project_hashes()
        protected = [name for name in baseline if name.endswith(('/work/cache.json', '/work/glossary.locked.json'))]
        self.assertEqual(len(protected), 6)
        self.assertEqual({k: current[k] for k in protected}, {k: baseline[k] for k in protected})

    def test_game_unchanged(self):
        self.assertEqual(p.game_hashes(), p.validate_sources()['game_hashes'])


if __name__ == '__main__':
    unittest.main()
