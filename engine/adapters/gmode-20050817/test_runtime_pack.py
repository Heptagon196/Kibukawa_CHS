import unittest
import ast
import io
import struct
from pathlib import Path
from types import SimpleNamespace
from runtime_pack import (compile_pack, target_rows, fullwidth,
                          row_target_markup, plain_segments, make_translation_pack, encode_translation_pack)

class RuntimePackTests(unittest.TestCase):
    def test_fullwidth(self):
        self.assertEqual(fullwidth('A 1!中文'), 'Ａ　１！中文')
        with self.assertRaises(ValueError): fullwidth('\U0001f600')

    def test_control_after_glyph(self):
        source = '<color=3>甲。</color><ctrl=2E/><row/><color=2>乙</color>'
        rows = target_rows(source, source)
        self.assertEqual(rows[0], dict(text='甲。', colors=[3,3], controls=[0,46]))
        self.assertEqual(rows[1]['controls'], [0])

    def test_empty_control_row_retains_event(self):
        rows = target_rows('<color=1>。</color><ctrl=2E/>', '<color=1></color><ctrl=2E/>')
        self.assertEqual(rows[0], dict(text='　', colors=[1], controls=[46]))

    def test_reject_changed_tags(self):
        with self.assertRaises(ValueError): target_rows('<color=1>甲</color>', '<color=2>乙</color>')

    def test_plain_segments_keep_event_boundaries_and_empty_targets(self):
        source = '<ctrl=01/><color=1>甲&amp;乙</color><ctrl=2E/><ctrl=2F/><color=2>丙</color><row/><color=3>丁</color>'
        target = '<ctrl=01/><color=1></color><ctrl=2E/><ctrl=2F/><color=2>A</color><row/><color=3>末</color>'
        self.assertEqual(plain_segments(source, target), [
            [dict(source='', target=''), dict(source='甲&乙', target=''),
             dict(source='', target=''), dict(source='丙', target='Ａ')],
            [dict(source='丁', target='末')]])
        self.assertEqual(plain_segments('<row/>', '<row/>'), [[], []])

    def test_row_markup_preserves_colors_controls_and_empty_rows(self):
        for row in [dict(text='', colors=[], controls=[]),
                    dict(text='甲乙　丙', colors=[1, 1, 2, 2], controls=[0, 46, 47, 0])]:
            markup = row_target_markup(row)
            self.assertEqual(target_rows(markup, markup), [row])
        self.assertEqual(row_target_markup(dict(text='甲乙', colors=[1,1], controls=[0,46])),
                         '<color=1>甲乙<ctrl=2E/></color>')

    def test_series_encoder_matches_previous_game(self):
        # Execute the actual preceding game's encoder, with only its destination
        # guard substituted, to check nullable fields and all four entry groups.
        previous = Path(__file__).resolve().parents[3]/'games/07-otonari/scripts/build_bepinex.py'
        tree = ast.parse(previous.read_text(encoding='utf-8-sig'))
        encoder = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'write_binary_pack')
        output = io.BytesIO()
        scope = dict(io=io, struct=struct,
                     p=SimpleNamespace(inside=lambda _: SimpleNamespace(write_bytes=output.write)))
        exec(compile(ast.Module(body=[encoder], type_ignores=[]), str(previous), 'exec'), scope)
        scripts = [dict(hash=bytes(range(32)), displays=[dict(offset=10, opcode=6,
                       rows=[dict(source='甲', text='乙', colors=[3], controls=[46],
                                  segments=[dict(source='甲', target='乙')])])],
                       strings=[dict(offset=55, opcode=17, source='丙', target='丁')])]
        pack = make_translation_pack(scripts, 'a'*64, 'b'*64,
                                     [dict(source='はい', target='是')],
                                     [dict(source='言語', target='语言', key='language')],
                                     [dict(index=1, token=2, instruction=3, source='戻る', target='返回', method='Menu')],
                                     script_names={bytes(range(32)).hex(): '1/scene01'})
        self.assertEqual([e['index'] for e in pack['scripts']], [0,1])
        self.assertEqual([e['slot'] for e in pack['scripts']], [0,-1])
        self.assertEqual(pack['scripts'][1]['instruction'], 55)
        self.assertEqual(pack['scripts'][0]['script'], '1/scene01')
        self.assertEqual(pack['scripts'][0]['target'], '乙')
        scope['write_binary_pack'](pack, 'translations.bin')
        self.assertEqual(encode_translation_pack(pack), output.getvalue())

    def test_complete_corpus(self):
        game = Path(__file__).resolve().parents[3]/'games/08-kibu8'
        if not (game/'raw').exists(): self.skipTest('Raw game assets unavailable')
        scripts, report = compile_pack(game)
        self.assertEqual(report['units'], 16636)
        self.assertEqual(report['ruby_groups'], 1910)
        self.assertEqual(report['unique_scripts'], 53)
        for script in scripts:
            for display in script['displays']:
                for row in display['rows']:
                    self.assertEqual(len(row['text']),len(row['colors']))
                    self.assertEqual(len(row['text']),len(row['controls']))
                    markup = row_target_markup(row)
                    decoded = target_rows(markup, markup)[0]
                    self.assertEqual(decoded, {key: row[key] for key in ('text','colors','controls')})
        names = {}
        for record in report['scripts']:
            names.setdefault(record['sha256'], record['name'])
        pack = make_translation_pack(scripts, 'a'*64, 'b'*64, [dict(source='はい', target='是')],
                                     script_names=names)
        self.assertEqual(len(pack['scripts']),
                         sum(len(r['segments']) for s in scripts for d in s['displays'] for r in d['rows'])+report['packed_strings'])
        self.assertTrue(all(e['script'] in names.values() for e in pack['scripts']))
        self.assertTrue(all('<color=' not in e['target'] and '<ctrl=' not in e['target']
                            and '<row/>' not in e['target'] for e in pack['scripts']))
        self.assertEqual(encode_translation_pack(pack), encode_translation_pack(pack))
        self.assertEqual(encode_translation_pack(pack)[:8], b'KBZH\x01\x00\x00\x00')

if __name__ == '__main__': unittest.main()
