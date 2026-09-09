"""Regression tests for shared color tags and instruction-boundary preservation."""
import shutil
import uuid
from contextlib import contextmanager
import unittest
from pathlib import Path
import dialogue_tags as d

@contextmanager
def workspace_temp():
    root=(Path(__file__).resolve().parents[1]/'reports/tag-tests').resolve()
    path=root/uuid.uuid4().hex;path.mkdir(parents=True)
    try:yield str(path)
    finally:
        assert path.resolve().is_relative_to(root) and path.resolve()!=root
        shutil.rmtree(path)

class TagsTests(unittest.TestCase):
    def test_all_six_reviewed_games(self):
        for n in range(1,7):
            p=d.resolve('kibu'+str(n))['project']
            with self.subTest(game=n):
                d.validate(p)
                cs,lookup,_=d.current(p)
                for layout,row in zip(d.layouts(cs,lookup,d.hard_breaks(p)),d.load(p/'work/dialogue-tagged.json')['units']):
                    slots=d.decode(layout,row['target'])
                    self.assertEqual(d.markup(layout,[''.join(slots[i] for i in g['ids']) for g in layout['groups']]),row['target'])

    def test_broken_color_and_dynamic_boundary(self):
        layout=dict(script='fixture',end=100,groups=[dict(color=None,ids=[1]),dict(color=5,ids=[2]),dict(color=5,ids=[3])])
        good=d.markup(layout,['共','次数','次'])
        for bad in [good.replace('RED','GREEN',1),good.replace('</color>','',1),good.replace('<boundary=3/>',''),good+'<color=5>新增</color>']:
            with self.subTest(target=bad),self.assertRaises(ValueError):d.decode(layout,bad)
        with self.assertRaises(ValueError):d.decode(layout,d.markup(layout,['字'*21,'次数','次']))

    def clone_second_game(self,dest):
        source=d.resolve('kibu2')['project']
        for name in ['work/manifest.json','work/cache.json','bepinex/build/replay.json','work/dialogue-tagged.json','research/color-spans.reviewed.json','project.json']:
            p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,p)
        return source

    def test_extract_before_first_build(self):
        with workspace_temp() as tmp:
            p=Path(tmp);self.clone_second_game(p)
            expected=d.document(p)
            (p/'bepinex/build/replay.json').rename(p/'research/source-replay.json')
            self.assertEqual(d.document(p),expected)

    def test_original_misalignment_is_rejected(self):
        with workspace_temp() as tmp:
            p=Path(tmp);source=self.clone_second_game(p)
            cache=d.load(p/'work/cache.json');before={x['id']:x['before'] for x in d.load(source/'work/color-migration.reviewed.json')['slots']}
            for f in cache['files'].values():
                for r in f['items']:
                    if r['text_index'] in before:r['translated_text']=before[r['text_index']]
            d.save(p/'work/cache.json',cache)
            with self.assertRaisesRegex(ValueError,'Tagged source/target differs'):d.validate(p)
            # Even re-exporting a corrupted cache cannot bypass independent color review.
            d.save(p/'work/dialogue-tagged.json',d.document(p))
            with self.assertRaisesRegex(ValueError,'Color semantics require review'):d.validate(p)

    def test_invalid_import_does_not_write_cache(self):
        with workspace_temp() as tmp:
            p=Path(tmp);self.clone_second_game(p)
            original=(p/'work/cache.json').read_bytes();config=(p/'project.json').read_bytes()
            doc=d.load(p/'work/dialogue-tagged.json')
            row=next(u for u in doc['units'] if '<color=' in u['target'])
            row['target']=row['target'].replace('</color>','',1);d.save(p/'work/dialogue-tagged.json',doc)
            with self.assertRaises(ValueError):d.import_document(p)
            self.assertEqual(original,(p/'work/cache.json').read_bytes());self.assertEqual(config,(p/'project.json').read_bytes())

    def test_unchanged_import_preserves_slots(self):
        with workspace_temp() as tmp:
            p=Path(tmp);self.clone_second_game(p);original=d.load(p/'work/cache.json')
            d.import_document(p)
            self.assertEqual(d.load(p/'work/cache.json'),original);d.validate(p)

if __name__=='__main__':unittest.main()
