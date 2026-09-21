"""Regression tests for the Chinese-content release gate."""
import unittest
from unittest.mock import patch

import quality_gate as gate
import verify_all


def unit(source, target, unit_id='file/test:1'):
    return dict(id=unit_id, active=True, source=source, target=target)


def document(*units):
    return dict(units=list(units))


class QualityGateTests(unittest.TestCase):
    def test_clean_text_passes(self):
        with patch.object(gate, 'ELLIPSIS', {}), patch.object(gate, 'COLOR_PUNCTUATION', {}):
            report = gate.inspect_document(document(unit('<color=0>原文。</color>', '<color=0>译文。</color>')))
        self.assertEqual('passed', report['status'])
        self.assertEqual([], report['findings'])

    def test_left_choice_width_is_limited_to_seven_chinese_cells(self):
        allowed = unit('七文字', '甲乙丙丁戊己庚', 'choice:1')
        allowed['kind'] = 'choice'
        too_wide = unit('八文字', '甲乙丙丁戊己庚辛', 'choice:2')
        too_wide['kind'] = 'choice'
        mixed = unit('日付', '从9月30日开始', 'choice:3')
        mixed['kind'] = 'choice'
        with patch.object(gate, 'ELLIPSIS', {}), patch.object(gate, 'COLOR_PUNCTUATION', {}):
            report = gate.inspect_document(document(allowed, too_wide, mixed))
        self.assertEqual({'choice:2', 'choice:3'},
                         {finding['id'] for finding in report['findings'] if finding['rule'] == 'choice_width'})
        self.assertEqual(84, gate.native_choice_width(allowed['target']))

    def test_empty_source_row_translation_is_rejected(self):
        value = unit('<color=0>第一行</color><row/><color=0>第二行</color>',
                     '<color=0>第一行</color><row/><color=0></color><ctrl=2E/>')
        with patch.object(gate, 'ELLIPSIS', {}), patch.object(gate, 'COLOR_PUNCTUATION', {}):
            report = gate.inspect_document(document(value))
        self.assertEqual(1, report['counts']['empty_target_row'])

    def test_redundant_chinese_punctuation_is_rejected(self):
        value = unit('<color=0>……</color>', '<color=0>……。然后，……</color>')
        with patch.object(gate, 'ELLIPSIS', {}), patch.object(gate, 'COLOR_PUNCTUATION', {}):
            report = gate.inspect_document(document(value))
        self.assertEqual(1, report['counts']['redundant_ellipsis_period'])
        self.assertEqual(1, report['counts']['redundant_comma_ellipsis'])

    def test_ascii_punctuation_and_japanese_quotes_are_rejected(self):
        value = unit('<color=0>原文</color>', '<color=0>「中文,测试」</color>')
        with patch.object(gate, 'ELLIPSIS', {}), patch.object(gate, 'COLOR_PUNCTUATION', {}):
            report = gate.inspect_document(document(value))
        self.assertEqual(1, report['counts']['mixed_ascii_chinese_punctuation'])
        self.assertEqual(1, report['counts']['japanese_quote_in_target'])

    def test_unreviewed_ellipsis_change_is_rejected(self):
        value = unit('<color=0>等……什么？</color>', '<color=0>等什么？</color>')
        with patch.object(gate, 'ELLIPSIS', {}), patch.object(gate, 'COLOR_PUNCTUATION', {}):
            report = gate.inspect_document(document(value))
        self.assertEqual(1, report['counts']['ellipsis_run_count'])

    def test_review_exception_is_bound_to_exact_content(self):
        value = unit('<color=0>等……什么？</color>', '<color=0>等什么？</color>')
        digest = gate.pair_digest(value['source'], value['target'])
        with patch.object(gate, 'ELLIPSIS', {value['id']: digest}), patch.object(gate, 'COLOR_PUNCTUATION', {}):
            self.assertEqual('passed', gate.inspect_document(document(value))['status'])
            value['target'] = '<color=0>等一下。</color>'
            report = gate.inspect_document(document(value))
        self.assertIn('ellipsis_run_count', report['counts'])
        self.assertIn('stale_reviewed_ellipsis_exception', report['counts'])

    def test_added_quote_and_punctuation_cannot_inherit_highlight(self):
        value = unit('<color=2>关键词</color>', '<color=2>‘关键词’，</color>')
        with patch.object(gate, 'ELLIPSIS', {}), patch.object(gate, 'COLOR_PUNCTUATION', {}):
            report = gate.inspect_document(document(value))
        self.assertEqual(1, report['counts']['added_quote_in_highlight'])
        self.assertEqual(1, report['counts']['added_terminal_punctuation_in_highlight'])

    def test_release_state_can_be_invalidated_before_checks(self):
        cache = {'extra': {'semantic_release_review_complete': True, 'translation_stage': 'reviewed'}}
        with patch.object(verify_all.p, 'load', return_value=cache), patch.object(verify_all.p, 'save') as save:
            verify_all.set_semantic_release_state(False, translation_stage='review_required')
        written = save.call_args.args[1]
        self.assertFalse(written['extra']['semantic_release_review_complete'])
        self.assertEqual('review_required', written['extra']['translation_stage'])


if __name__ == '__main__':
    unittest.main()
