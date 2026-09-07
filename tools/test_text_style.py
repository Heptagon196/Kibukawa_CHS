import unittest
from check_text_style import inspect_rows


def row(index, text, opcode=72, status=1):
    return dict(text_index=index, translated_text=text, translation_status=status,
                extra=dict(location=dict(kind='script', asset='test.res', member='scn0', opcode=opcode)))


class StyleAuditTests(unittest.TestCase):
    def test_fragment_and_nested_quotes(self):
        self.assertEqual(inspect_rows([row(1, '“他说‘你'), row(2, '好’。”')]), [])

    def test_missing_close_before_next_speaker(self):
        findings = inspect_rows([row(1, '“你好。'), row(2, '“再见。”')])
        self.assertEqual([(x['id'], x['rule']) for x in findings], [(1, 'quote_unclosed')])

    def test_menu_cannot_close_dialogue(self):
        findings = inspect_rows([row(1, '“你好'), row(2, '再见。”', opcode=73)])
        self.assertEqual({x['rule'] for x in findings}, {'quote_unclosed', 'quote_unmatched_close'})

    def test_spaces_and_exclusions(self):
        findings = inspect_rows([row(1, ' 旅游的意思呢。'), row(2, 'hello world'),
                                 row(3, '　　'), row(4, '中文 空格'), row(5, ' 忽略', status=7)])
        self.assertEqual([(x['id'], x['rule']) for x in findings],
                         [(1, 'spacing_edge'), (3, 'spacing_layout'), (4, 'spacing_inside')])


if __name__ == '__main__':
    unittest.main()
