"""Regression tests: omissions, stale source, line and placeholder-sensitive data."""
import copy
import unittest
from check_ui import key_problems


class UiSourceTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{'Key': 'confirm', 'ja': '確認\nしますか？'}]
        self.entries = [{'key': 'confirm', 'source_text': '確認\nしますか？', 'target_text': '是否\n确认？'}]

    def test_complete_table(self):
        self.assertEqual(key_problems(self.rows, self.entries), [])

    def test_missing_key(self):
        self.assertTrue(key_problems(self.rows, []))

    def test_stale_source(self):
        entries = copy.deepcopy(self.entries)
        entries[0]['source_text'] = '旧原文'
        self.assertTrue(key_problems(self.rows, entries))

    def test_lost_line(self):
        entries = copy.deepcopy(self.entries)
        entries[0]['target_text'] = '是否确认？'
        self.assertTrue(key_problems(self.rows, entries))

    def test_duplicate_key(self):
        self.assertTrue(key_problems(self.rows, self.entries * 2))


if __name__ == '__main__':
    unittest.main()
