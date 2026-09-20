"""Regressions for direct-container translation pack and review gates."""
import copy
import unittest
from unittest.mock import patch
import pipeline as p
import runtime_pack as pack
import translation_review as review

class BuildTests(unittest.TestCase):
    def test_original_codec_pack_coverage(self):
        scripts,report=pack.compile_pack(p.WORK,smoke=True)
        self.assertEqual((9541,309,36),(report['units'],report['inactive_units'],len(scripts)))
        self.assertEqual(9541,report['packed_displays']+report['packed_strings'])
        self.assertTrue(any(t['opcode']==73 for s in scripts for t in s['strings']))
        for script in scripts:
            for display in script['displays']:
                for row in display['rows']:
                    self.assertEqual(len(row['text']),len(row['controls']))
                    self.assertEqual(len(row['text']),len(row['colors']))

    def test_structural_controls_cannot_move(self):
        source='<color=0>原</color><ctrl=2E/><color=1>文</color>'
        with self.assertRaises(ValueError):
            pack.target_rows(source,'<color=0>译文</color><color=1>文</color><ctrl=2E/>')
        rows=pack.target_rows(source,'<color=0>译</color><ctrl=2E/><color=1>文</color>')
        self.assertEqual([46,0],rows[0]['controls'])

    def test_strict_missing_review_refused(self):
        original=p.load
        def load(path):
            if str(path).endswith('.reviewed.json'):
                return dict(adapter='gmode-20050817-direct',units=[])
            return original(path)
        with patch.object(p,'load',side_effect=load),patch.object(p,'save'):
            with self.assertRaises(ValueError): review.check(strict=True)

    def test_click_ids_unique_and_source_retained(self):
        candidates=review.candidates()
        for group in candidates.values():
            self.assertEqual(len(group),len({u['id'] for u in group}))
        self.assertTrue(any('source' in span for u in candidates['clicks'] for span in u['spans']))

if __name__=='__main__': unittest.main()
