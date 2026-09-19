"""Offline invariants for the ninth-title pack builder against the shipped scripts."""
import pathlib
import unittest
from runtime_pack import (RUN_SEPARATOR, build, colour_lines, emphasis_runs, line_index, script_lines,
                          single_texts, text_budget)
from vm import NAMAE_SETTEI, SENTAKUSI, parse_bin

ROOT = pathlib.Path(__file__).resolve().parents[3]
RAW = ROOT / 'games/09-samidare/raw'
ASSEMBLY = 'a' * 64
SCRATCH = 'b' * 64
UI = [dict(source='閉じる', target='继续游戏', key='close')]


def scripts():
    result = {}
    for path in sorted(RAW.rglob('*.bin')):
        if path.name == 'scn0.bin':
            continue
        result[path.stem] = path.read_bytes()
    return result


class GroupingTests(unittest.TestCase):
    def test_every_shipped_line_matches_its_declared_length(self):
        """The third setup byte is the line's own length, so it validates the grouping."""
        total = 0
        for name, raw in scripts().items():
            with self.subTest(script=name):
                lines = script_lines(raw)
                total += len(lines)
                for line in lines:
                    if line['declared']:
                        self.assertEqual(line['declared'], len(line['text']))
                    if line['limit']:
                        self.assertLessEqual(len(line['text']), line['limit'])
        self.assertEqual(total, 7298)

    def test_line_offsets_are_unique_and_indexed(self):
        for name, raw in scripts().items():
            with self.subTest(script=name):
                lines = script_lines(raw)
                index = line_index(lines, name)
                self.assertEqual(len(index), len(lines))
                for line in lines:
                    self.assertIs(index[line['offset']], line)

    def test_fragments_concatenate_into_the_line(self):
        for name, raw in scripts().items():
            with self.subTest(script=name):
                for line in script_lines(raw):
                    self.assertEqual(''.join(line['fragments']), line['text'])
                    self.assertGreaterEqual(len(line['fragments']), 1)


class TextTests(unittest.TestCase):
    def test_nameplates_and_labels_are_found_by_offset(self):
        names = choices = 0
        for name, raw in scripts().items():
            with self.subTest(script=name):
                texts = single_texts(parse_bin(raw))
                for offset, entry in texts.items():
                    self.assertIn(entry['kind'], ('name', 'choice'))
                    self.assertTrue(entry['source'])
                    self.assertEqual(entry['offset'], offset)
                    if entry['kind'] == 'name':
                        names += 1
                        self.assertEqual(entry['opcode'], NAMAE_SETTEI)
                        self.assertTrue(entry['source'].startswith('('), 'nameplate text keeps its parentheses')
                    else:
                        choices += 1
                        self.assertEqual(entry['opcode'], SENTAKUSI)
        # The shipped corpus is fixed; a change here means the parser or the operand
        # index for a text command moved.
        self.assertEqual(names, 34)
        self.assertEqual(choices, 174)

    def test_budget_is_the_longest_shipped_string_per_kind(self):
        entries = [entry for raw in scripts().values() for entry in single_texts(parse_bin(raw)).values()]
        budgets = text_budget(entries)
        self.assertEqual(budgets['name'], 7)
        self.assertEqual(budgets['choice'], 11)

    def test_pack_marks_each_kind_with_its_own_opcode(self):
        texts = {name: single_texts(parse_bin(raw)) for name, raw in scripts().items()}
        name_entry = next(entry for group in texts.values() for entry in group.values() if entry['kind'] == 'name')
        choice_entry = next(entry for group in texts.values() for entry in group.values() if entry['kind'] == 'choice')
        units = [dict(script=script, offset=entry['offset'], source=entry['source'],
                      target=('(' + '甲' * (len(entry['source']) - 2) + ')'
                              if entry['kind'] == 'name' else '甲' * len(entry['source'])))
                 for script, group in texts.items() for entry in group.values()
                 if entry is name_entry or entry is choice_entry]
        pack = build(scripts(), units, UI, ASSEMBLY, SCRATCH, complete=False)
        opcodes = sorted(entry['opcode'] for entry in pack['scripts'])
        self.assertEqual(opcodes, sorted([NAMAE_SETTEI, SENTAKUSI]))
        packed_name = next(entry for entry in pack['scripts'] if entry['opcode'] == NAMAE_SETTEI)
        packed_choice = next(entry for entry in pack['scripts'] if entry['opcode'] == SENTAKUSI)
        self.assertEqual(packed_name['slot'], 1,
                         'single-string nameplate must not claim continuations')
        self.assertEqual(packed_choice['slot'], 1,
                         'single-string choice must not claim continuations')

    def test_rejects_a_label_over_the_corpus_budget(self):
        choice = next(entry for group in (single_texts(parse_bin(raw)) for raw in scripts().values())
                      for entry in group.values() if entry['kind'] == 'choice')
        unit = dict(script='c0_00', offset=choice['offset'], source=choice['source'], target='甲' * 12)
        with self.assertRaisesRegex(ValueError, 'exceeds the native choice budget'):
            build(scripts(), [unit], UI, ASSEMBLY, SCRATCH, complete=False)

    def test_rejects_nameplate_that_changes_halfwidth_parentheses(self):
        for script, raw in scripts().items():
            name = next((entry for entry in single_texts(parse_bin(raw)).values()
                         if entry['kind'] == 'name'), None)
            if name is None:
                continue
            target = '（' + name['source'][1:-1] + '）'
            unit = dict(script=script, offset=name['offset'], source=name['source'], target=target)
            with self.assertRaisesRegex(ValueError, 'preserve its ASCII parentheses'):
                build(scripts(), [unit], UI, ASSEMBLY, SCRATCH, complete=False)
            return
        self.fail('Shipped corpus has no nameplate fixture')

    def test_rejects_nameplate_wider_than_its_own_authored_width(self):
        for script, raw in scripts().items():
            name = next((entry for entry in single_texts(parse_bin(raw)).values()
                         if entry['kind'] == 'name'), None)
            if name is None:
                continue
            target = '(' + '甲' * (len(name['source']) - 1) + ')'
            unit = dict(script=script, offset=name['offset'], source=name['source'], target=target)
            with self.assertRaisesRegex(ValueError, 'authored display width'):
                build(scripts(), [unit], UI, ASSEMBLY, SCRATCH, complete=False)
            return
        self.fail('Shipped corpus has no nameplate fixture')


class BuildTests(unittest.TestCase):
    def first_line(self, name):
        lines = script_lines(scripts()[name])
        return lines[0]

    def test_accepts_a_line_that_fits_the_budget(self):
        line = self.first_line('c0_00')
        unit = dict(script='c0_00', offset=line['offset'], source=line['text'], target='甲' * line['limit'])
        pack = build(scripts(), [unit], UI, ASSEMBLY, SCRATCH, complete=False)
        self.assertEqual(pack['schema'], 1)
        self.assertEqual(pack['scripts'][0]['instruction'], line['offset'])
        self.assertEqual(pack['scripts'][0]['slot'], len(line['fragments']))
        self.assertEqual(pack['scripts'][0]['target'], '甲' * line['limit'])

    def test_rejects_a_target_over_the_native_budget(self):
        line = self.first_line('c0_00')
        unit = dict(script='c0_00', offset=line['offset'], source=line['text'], target='甲' * (line['limit'] + 1))
        with self.assertRaisesRegex(ValueError, 'exceeds the native line budget'):
            build(scripts(), [unit], UI, ASSEMBLY, SCRATCH, complete=False)

    def test_rejects_unknown_script_offset_and_stale_source(self):
        line = self.first_line('c0_00')
        cases = {
            'script': dict(script='c9_99', offset=line['offset'], source=line['text'], target='甲'),
            'offset': dict(script='c0_00', offset=0x7FFF, source=line['text'], target='甲'),
            'source': dict(script='c0_00', offset=line['offset'], source='ちがう', target='甲'),
        }
        for label, unit in cases.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                build(scripts(), [unit], UI, ASSEMBLY, SCRATCH, complete=False)

    def test_rejects_duplicate_entries_and_requires_completeness_when_asked(self):
        line = self.first_line('c0_00')
        unit = dict(script='c0_00', offset=line['offset'], source=line['text'], target='甲')
        with self.assertRaisesRegex(ValueError, 'Duplicate draft entry'):
            build(scripts(), [unit, dict(unit)], UI, ASSEMBLY, SCRATCH, complete=False)
        with self.assertRaisesRegex(ValueError, 'Untranslated display text remains'):
            build(scripts(), [unit], UI, ASSEMBLY, SCRATCH, complete=True)

    def test_requires_scripts_and_ui(self):
        line = self.first_line('c0_00')
        unit = dict(script='c0_00', offset=line['offset'], source=line['text'], target='甲')
        with self.assertRaises(ValueError):
            build(scripts(), [unit], [], ASSEMBLY, SCRATCH, complete=False)


class EmphasisTests(unittest.TestCase):
    """IRO starts and F7 ends the exact character range drawn in another colour."""

    def test_runs_are_the_line_text_split_and_nothing_else(self):
        lines = splits = 0
        for name, raw in scripts().items():
            with self.subTest(script=name):
                parsed = parse_bin(raw)
                index = line_index(script_lines(raw), name)
                for offset, runs in emphasis_runs(parsed).items():
                    lines += 1
                    splits += len(runs) - 1
                    self.assertEqual(''.join(run['text'] for run in runs), index[offset]['text'])
                    self.assertTrue(all(run['text'] for run in runs))
                    self.assertTrue(any(run['colour'] != runs[0]['colour'] for run in runs[1:]))
        # Pinned to the shipped corpus: a change to the line terminators or to the
        # colour opcode moves these numbers instead of silently dropping emphasis.
        self.assertEqual(lines, 287)
        self.assertEqual(splits, 401)

    def test_an_emphasised_clue_keeps_its_split(self):
        runs = emphasis_runs(parse_bin(scripts()['c0_00']))[0x3E9C]
        self.assertEqual(runs, [dict(colour=None, text='実はこの子、'),
                                dict(colour=2, text='家出'),
                                dict(colour=None, text='して')])

    def test_f7_after_ruby_closes_ruby_before_it_restores_colour(self):
        runs = emphasis_runs(parse_bin(scripts()['c3_01']))[4243]
        self.assertEqual(runs, [dict(colour=2, text='螻川内忠雄'),
                                dict(colour=None, text='の名前も')])

    def test_whole_colour_lines_are_in_the_full_inventory(self):
        whole = 0
        for raw in scripts().values():
            whole += sum(len(runs) == 1 and runs[0]['colour'] is not None
                         for runs in colour_lines(parse_bin(raw)).values())
        self.assertEqual(whole, 126)

    def test_single_colour_lines_are_not_reported(self):
        parsed = parse_bin(scripts()['c0_00'])
        reported = set(emphasis_runs(parsed))
        plain = [line for line in script_lines(scripts()['c0_00'])
                 if line['offset'] not in reported]
        self.assertTrue(plain)
        self.assertTrue(all(len(line['fragments']) >= 1 for line in plain))


class ColourRunTests(unittest.TestCase):
    """A recoloured line travels to the runtime as one string per colour run."""

    OFFSET = 0x3E9C          # c0_00: 実はこの子、|家出して, the second run in colour 2
    SOURCE = '実はこの子、家出して'

    def unit(self, **overrides):
        unit = dict(script='c0_00', offset=self.OFFSET, source=self.SOURCE,
                    target='其实这孩子，离家出走', runs=['其实这孩子，', '离家出走', ''])
        unit.update(overrides)
        return unit

    def test_the_pack_joins_the_runs_with_the_separator(self):
        self.assertEqual(RUN_SEPARATOR, '\x01')
        pack = build(scripts(), [self.unit()], UI, ASSEMBLY, SCRATCH, complete=False)
        entry = pack['scripts'][0]
        self.assertEqual(entry['target'], '其实这孩子，' + RUN_SEPARATOR + '离家出走' + RUN_SEPARATOR)
        self.assertEqual(entry['slot'], 3)
        # The separator is a packing detail: the shipped source never contains it.
        self.assertNotIn(RUN_SEPARATOR, entry['source'])

    def test_a_recoloured_line_without_runs_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'must give one run per colour'):
            build(scripts(), [self.unit(runs=None)], UI, ASSEMBLY, SCRATCH, complete=False)

    def test_the_run_count_must_match_the_script(self):
        with self.assertRaisesRegex(ValueError, 'but its translation has 1 runs'):
            build(scripts(), [self.unit(runs=['其实这孩子，离家出走'])], UI, ASSEMBLY, SCRATCH,
                  complete=False)

    def test_the_runs_must_join_into_the_target(self):
        with self.assertRaisesRegex(ValueError, 'do not join into its translation'):
            build(scripts(), [self.unit(runs=['其实这孩子', '离家出走了', ''])], UI, ASSEMBLY, SCRATCH,
                  complete=False)

    def test_a_single_colour_line_takes_a_plain_translation(self):
        line = script_lines(scripts()['c0_00'])[0]
        self.assertNotIn(line['offset'], emphasis_runs(parse_bin(scripts()['c0_00'])))
        unit = dict(script='c0_00', offset=line['offset'], source=line['text'],
                    target='甲', runs=['甲'])
        with self.assertRaisesRegex(ValueError, 'takes a plain translation'):
            build(scripts(), [unit], UI, ASSEMBLY, SCRATCH, complete=False)


if __name__ == '__main__':
    unittest.main()
