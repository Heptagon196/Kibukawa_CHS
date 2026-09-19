"""Reflow regression against every shipped scene and its actual control commands."""
import json
import re
import unittest
from pathlib import Path

import build_pack as b
import dialogue_layout as d


class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scripts = b.scenario_scripts()
        cls.units = b.runtime_pack.load_draft(b.p.WORK / b.DRAFT)
        folder = b.p.WORK / 'bepinex/build/layout-tests'
        folder.mkdir(parents=True, exist_ok=True)
        d.build(cls.scripts, cls.units, b'test pack', folder)
        cls.report = json.loads((folder / 'dialogue-layout.json').read_text('utf-8'))

    def test_screenshot(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c0_01' and e['offsets'][0] == 1306)
        self.assertEqual('…您一个人也聊得这么起劲啊。', ''.join(example['after']))

    def test_scenery_is_a_word(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c0_00' and e['offsets'][0] == 1006)
        self.assertIn('景物', example['tokens'])
        self.assertEqual(['黑白色的', '景物默默地…'], example['after'])

    def test_izuna_sarcasm_keeps_the_speaker_as_the_target(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c0_01' and e['offsets'][0] == 5402)
        self.assertEqual(['这什么意思啊，', '是在挖苦我吗？', '根本就是挖苦嘛！'],
                         example['after'])

    def test_office_move_reads_naturally_in_context(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c0_01' and e['offsets'][0] == 5347)
        self.assertEqual(['还不能搬到', '更好的地方吗？'], example['after'])

    def test_guest_name_and_title_stay_together(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c0_01' and e['offsets'][0] == 7176)
        self.assertEqual(['本期嘉宾是', '侦探助手', '白鹭洲伊纲小姐！'], example['after'])

    def test_office_name_stays_together(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c0_01' and e['offsets'][0] == 8640)
        self.assertEqual(['请问，这里是', '癸生川侦探事务所？'], example['after'])

    def test_leading_ellipsis_stays_on_authored_next_row(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c1_00' and e['offsets'][0] == 676)
        self.assertEqual(['喂，癸生川。', '…不在吗？'], example['after'])

    def test_all_authored_leading_ellipsis_breaks_are_preserved(self):
        for example in self.report['examples']:
            source_cursor = 0
            required = set()
            for index, row in enumerate(example['before'][:-1]):
                source_cursor += len(row)
                if example['before'][index + 1].startswith('…'):
                    required.add(source_cursor)
            rendered_cursor = 0
            rendered = set()
            for row in example['after'][:-1]:
                rendered_cursor += len(row)
                rendered.add(rendered_cursor)
            self.assertTrue(required <= rendered,
                            '%s:%s lost leading ellipsis break: %r -> %r' %
                            (example['script'], example['offsets'][0],
                             example['before'], example['after']))

    def test_opening_quote_starts_the_quoted_row(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c1_01' and e['offsets'][0] == 537)
        self.assertEqual(['招牌上写着：', '“癸生川侦探事务所”',
                          '…就是这个名字。'], example['after'])

    def test_misread_name_stays_on_its_authored_row(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c1_01' and e['offsets'][0] == 904)
        self.assertEqual(['…话说这个姓', '到底怎么念？',
                          '“葵生川”…吗？'], example['after'])

    def test_full_width_number_is_not_split(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c1_01' and e['offsets'][0] == 3459)
        self.assertEqual(['我明明才', '２５岁啊…'], example['after'])

    def test_no_unicode_number_is_split_in_the_corpus(self):
        for example in self.report['examples']:
            text = ''.join(example['after'])
            cursor = 0
            for row in example['after'][:-1]:
                cursor += len(row)
                self.assertFalse(text[cursor - 1].isdigit() and text[cursor].isdigit(),
                                 '%s:%s split number: %r' %
                                 (example['script'], example['offsets'][0],
                                  example['after']))

    def test_complete_sentence_is_not_merged_with_the_next_one(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c1_01' and e['offsets'][0] == 4051)
        self.assertEqual(['蝼川内先生，对吧。', '请多关照。'], example['after'])

    def test_ellipsis_quantities_follow_the_authored_text(self):
        runs = lambda text: [len(match.group()) for match in re.finditer('…+', text)]
        pure_pause = lambda text: not text.strip('…。，！？!?、,.；;：:—－・ ·\t\r\n')
        for unit in self.units:
            if unit.get('kind', 'line') != 'line':
                continue
            source_runs = runs(unit['source'])
            target = unit.get('target', '')
            target_runs = runs(target)
            if not target_runs:
                continue
            if source_runs and len(source_runs) == len(target_runs):
                self.assertEqual(source_runs, target_runs,
                                 '%s:%s changed ellipsis length' %
                                 (unit['script'], unit['offset']))
            elif source_runs and max(source_runs) == 1:
                self.assertTrue(all(length == 1 for length in target_runs))
            elif not source_runs and not pure_pause(target):
                self.assertTrue(all(length == 1 for length in target_runs))

    def test_highlighted_name_stays_on_the_highlighted_native_row(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c3_01' and e['offsets'][0] == 4204)
        self.assertEqual(['而其中，', '蝼川内忠雄的名字', '也赫然在列。'],
                         example['after'])

    def test_highlighted_residence_is_a_complete_sentence(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c3_01' and e['offsets'][0] == 4435)
        self.assertEqual(['…地址在川北市…', '工厂附近的另一处',
                          '住宅似乎也是他的。'], example['after'])
        self.assertIn('另一处住宅', ''.join(example['after']))

    def test_english_contraction_and_words_are_not_split_or_joined(self):
        example = next(e for e in self.report['examples']
                       if e['script'] == 'c3_01' and e['offsets'][0] == 14308)
        rendered = '\n'.join(example['after'])
        self.assertIn("MILK DOESN'T RETURN!", ' '.join(rendered.split()))
        self.assertNotIn("DOESN'\nT", rendered)
        self.assertNotIn("DOESN'TRETURN", ''.join(example['after']))

    def test_all_authored_leading_quote_breaks_are_preserved(self):
        for example in self.report['examples']:
            source_cursor = 0
            required = set()
            for index, row in enumerate(example['before'][:-1]):
                source_cursor += len(row)
                if example['before'][index + 1].startswith(('“', '‘')):
                    required.add(source_cursor)
            rendered_cursor = 0
            rendered = set()
            for row in example['after'][:-1]:
                rendered_cursor += len(row)
                rendered.add(rendered_cursor)
            self.assertTrue(required <= rendered,
                            '%s:%s lost leading quote break: %r -> %r' %
                            (example['script'], example['offsets'][0],
                             example['before'], example['after']))

    def test_entire_corpus_does_not_split_tokens_without_review(self):
        for e in self.report['examples']:
            cursor, cuts = 0, set()
            for row in e['after'][:-1]:
                cursor += len(row)
                cuts.add(cursor)
            cursor = 0
            for token in e['tokens']:
                if cuts.intersection(range(cursor + 1, cursor + len(token))):
                    self.fail('token split at %s:%s: %s in %r' %
                              (e['script'], e['offsets'][0], token, e['after']))
                cursor += len(token)
            if len(e['after']) > 1:
                final = e['after'][-1]
                if len(final.strip('，。！？…')) < 2:
                    self.assertEqual(e['before'][-1], final)

    def test_entire_corpus_fits_and_preserves_every_character(self):
        for e in self.report['examples']:
            self.assertEqual(''.join(e['before']), ''.join(e['after']))
            self.assertLessEqual(len(e['after']), len(e['before']))
            for i, row in enumerate(e['after']):
                self.assertLessEqual(d.width(row), e['block_width'])
                self.assertEqual((240 - e['block_width']) // 2, e['margin'])
                if i and row[0] != '…':
                    self.assertNotIn(row[0], d.CLOSE)
                if i + 1 < len(e['after']):
                    self.assertNotIn(row[-1], d.OPEN)

    def test_no_group_crosses_click_clear_speaker_branch_or_label(self):
        parsed = {s: d.parse_bin(raw) for s, raw in self.scripts.items()}
        allowed = {244, 245, 246, 247, 248, 249, 250, 255}
        for e in self.report['examples']:
            first, last = e['offsets'][0], e['offsets'][-1]
            source = parsed[e['script']]
            self.assertFalse(any(first < label <= last for label in source['labels']))
            between = [c for c in source['commands'] if first < c['offset'] < last]
            self.assertTrue(all(c['opcode'] in allowed for c in between))
            self.assertEqual(len(e['offsets']) - 1, sum(c['opcode'] == 244 for c in between))

    def test_latin_word_and_punctuation(self):
        rows, _ = d.positions('这是一个用于检查英文排版的ABC案件。')
        self.assertTrue(any('ABC' in row for row in rows))
        rows, _ = d.positions('中' * 13 + '，然后继续。')
        self.assertTrue(all(row[0] not in d.CLOSE for row in rows[1:]))
        rows, _ = d.positions('中' * 13 + '（这是一段括号）')
        self.assertTrue(all(row[-1] not in d.OPEN for row in rows[:-1]))


if __name__ == '__main__':
    unittest.main()
