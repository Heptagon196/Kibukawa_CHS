"""Offline puzzle invariants and original branch compatibility; no game launch."""
import io
import itertools
import re
import unittest
import zipfile
import pipeline as p
from review_units import current
from click_boundaries import units

KEY = {c:n for n,s in enumerate(['ABC','DEF','GHI','JKL','MNO','PQRS','TUV','WXYZ'],2) for c in s}
SPELLINGS = {'田中':'TIANZHONG','广美':'GUANGMEI','内野':'NEIYE','玛雅':'MAYA',
             '楢原':'YOUYUAN','康司':'KANGSI','夏目':'XIAMU','政隆':'ZHENGLONG',
             '松井':'SONGJING','爱香':'AIXIANG','原':'YUAN','西野':'XIYE'}
def score(name): return sum(KEY[c] for c in SPELLINGS[name])

class PuzzleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache=p.load(p.WORK/'work/cache.json')
        cls.rows={r['text_index']:r for f in cache['files'].values() for r in f['items']}
        commands,lookup=current()
        cls.texts={next(lookup[(u['script'],i)]['text_index'] for i in u['instructions'] if (u['script'],i) in lookup):u['target'] for u in units(commands)}
        assets=p.text_assets(p.GAME/(p.STREAM+'file'))
        archive=zipfile.ZipFile(io.BytesIO(p.text_assets(p.GAME/(p.STREAM+'scratchpad'))['tuikousaku.res']))
        cls.commands={c['offset']:c for c in p.parse_script(archive.read('scn5'),p.definitions(assets['define']))}
        cls.opening=p.parse_script(archive.read('scn10'),p.definitions(assets['define']))

    def test_numeric_chain_and_unique_name_choices(self):
        remaining=200
        for start,correct,difference,result in zip([4206,4211,4216,4221,4227],[0,1,0,1,1],[37,19,48,29,42],[163,144,96,67,25]):
            options=[self.rows[start+j]['translated_text'] for j in range(2)]
            self.assertEqual([j for j,n in enumerate(options) if score(n)==difference],[correct])
            remaining-=score(options[correct]);self.assertEqual(remaining,result)
            # Verify the actual original bytecode: correct label takes continuation,
            # the alternative takes the common failure branch. No assumed menu order.
            loc=self.rows[start]['extra']['location'];command=self.commands[loc['instruction']]
            self.assertEqual(command['opcode'],106)
            targets=[a['value'] for a in command['args'] if a['kind']==4][:2]
            self.assertEqual(targets[correct],command['end'])
            self.assertEqual(targets[1-correct],15267)
        self.assertEqual(remaining-score('原'),0)
        self.assertEqual(remaining-score('西野'),0)
        # Inner surname also totals 25, but that person is already dead.
        self.assertEqual(score('内野'),25)
        self.assertIn('尚未遇害',self.texts[4965])

    def test_opening_has_original_level_of_key_ambiguity(self):
        starts=[7135,7145,7155,7165];echoes=[7174,7182,7190,7198]
        options=[[self.rows[s+j]['translated_text'] for j in range(8)] for s in starts]
        for opts,echo in zip(options,echoes):
            self.assertEqual(len(set(opts)),8)
            self.assertEqual(opts,[self.rows[echo+j]['translated_text'] for j in range(8)])
        valid=[indices for indices in itertools.product(range(8),repeat=4)
               if ''.join(str(KEY[options[k][v]]) for k,v in enumerate(indices))=='9878']
        self.assertEqual(valid,[(3,1,4,6),(4,1,4,6)])
        self.assertEqual({''.join(options[k][v] for k,v in enumerate(path)) for path in valid},{'ZUPU','YUPU'})
        self.assertEqual(''.join(options[k][v] for k,v in enumerate((4,1,4,6))),'YUPU')
        self.assertIn('９８７８',self.texts[7095])
        self.assertIn('YUPU，就是鱼铺',self.texts[7207])

    def test_original_opening_score_increments_match_the_new_solution(self):
        condition=None;credited=[]
        for command in self.opening:
            if not 5635<=command['offset']<=6034:continue
            args=[a['value'] for a in command['args']]
            if command['opcode']==2:
                self.assertEqual(args[1],0)
                condition=(args[0],args[2])
            if command['opcode']==11:
                self.assertEqual(args,[39,1,1])
                credited.append(condition)
        self.assertEqual(credited,[(31,5),(32,2),(33,5),(34,7)])

    def test_no_old_clues_or_notes_and_card_numbers(self):
        text=''.join(r['translated_text'] for r in self.rows.values() if r['translation_status']!=7)
        for old in ['鱼吧','YUBA','９８２２','两位或三位数','译注','滨川','a段','五十音','平假名','３２５８','sakanaya','tanaka','narahara','masataka','manaka','ha、ra']:
            self.assertNotIn(old,text)
        for ids in [[1416,1419,1422,1425],[2880,2883,2886,2889],[4412,4415,4418,4421]]:
            self.assertEqual([self.rows[i]['translated_text'].split('…')[1] for i in ids],['１６３','１４４','９６','６７'])
        self.assertTrue(self.rows[4424]['translated_text'].endswith('２５'))
        for r in self.rows.values():
            if r['translation_status']!=7 and r['extra']['location']['kind']=='script':
                self.assertLessEqual(len(r['translated_text'].encode('utf-16-le'))//2,20)

if __name__=='__main__':unittest.main()
