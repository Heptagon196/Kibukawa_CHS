"""Regression coverage for the shared review gate, without game-window access."""
import json
import shutil
import uuid
from contextlib import contextmanager
import unittest
from pathlib import Path
from click_boundaries import units, validate, compare, PROFILES

@contextmanager
def fixture_directory():
    root=Path(__file__).resolve().parents[1]/'reports'
    root.mkdir(exist_ok=True)
    path=root/('click-test-'+uuid.uuid4().hex)
    path.mkdir()
    try:yield path
    finally:
        assert path.resolve().parent==root.resolve() and path.name.startswith('click-test-')
        shutil.rmtree(path)

def cmd(offset, op, source='', target='', script='scn0'):
    return dict(script=script,instruction=offset,opcode=op,strings=[source],expected=[target])

class ClickReviewTests(unittest.TestCase):
    def test_visual_wrap_and_real_wait(self):
        commands=[cmd(0,72,'部屋へ','去房间吧！'),cmd(1,77),cmd(2,72,'行こう',''),cmd(3,78),cmd(4,72,'十六階','在十六楼！'),cmd(5,76)]
        for adapter in PROFILES:
            result=units(commands,adapter)
            self.assertEqual([u['target'] for u in result],['去房间吧！','在十六楼！'])
            self.assertEqual(result[0]['instructions'],[0,2])

    def test_all_boundaries_and_script_switch(self):
        for op in (71,73,75,76,78,79,105,129):
            self.assertEqual(len(units([cmd(0,72,'一','甲'),cmd(1,op),cmd(2,72,'二','乙')])),2)
        self.assertEqual(len(units([cmd(0,72,'一','甲'),cmd(0,72,'二','乙',script='scn1')])),2)
        with self.assertRaises(ValueError):units([cmd(0,72),cmd(0,72)])
        with self.assertRaises(ValueError):units([], 'unknown-engine')

    def test_missing_baseline_and_changed_text_cannot_pass(self):
        with fixture_directory() as directory:
            project=Path(directory);(project/'work').mkdir()
            (project/'project.json').write_text(json.dumps(dict(id='fixture',adapter='gmode-v1')))
            (project/'work/cache.json').write_text('{}')
            commands=[cmd(0,72,'十六階','在十六楼！'),cmd(1,78)]
            baseline=project/'work/click_boundaries.reviewed.json'
            with self.assertRaises(ValueError):validate(commands,project)
            self.assertFalse(baseline.exists())
            baseline.write_text(json.dumps(dict(units=units(commands))))
            approved=baseline.read_bytes()
            self.assertEqual(validate(commands,project)['status'],'passed')
            commands[0]['expected'][0]='在十'
            with self.assertRaises(ValueError):validate(commands,project)
            self.assertEqual(baseline.read_bytes(),approved)
            self.assertEqual(validate([],project,strict=False)['status'],'review_required')

    def test_source_and_boundary_edits_invalidate_review(self):
        original=units([cmd(0,72,'原文','译文'),cmd(1,78)])
        for commands in ([cmd(0,72,'新原文','译文'),cmd(1,78)], [cmd(0,72,'原文','译文'),cmd(2,78)]):
            changed,_,unchanged=compare(units(commands),original)
            self.assertTrue(changed);self.assertEqual(unchanged,0)
        with self.assertRaises(ValueError):compare(original,original+original)

if __name__=='__main__':unittest.main()
