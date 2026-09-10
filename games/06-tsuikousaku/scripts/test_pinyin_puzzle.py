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
SPELLINGS = {'浅边':'QIANBIAN','广美':'GUANGMEI','内野':'NEIYE','千怜':'QIANLIAN',
             '边见':'BIANJIAN','康司':'KANGSI','夏目':'XIAMU','健典':'JIANDIAN',
             '松井':'SONGJING','怜见':'LIANJIAN','田边':'TIANBIAN','千典':'QIANDIAN'}
SYLLABLES = {'浅边':['qian','bian'],'广美':['guang','mei'],'内野':['nei','ye'],'千怜':['qian','lian'],
             '边见':['bian','jian'],'康司':['kang','si'],'夏目':['xia','mu'],'健典':['jian','dian'],
             '松井':['song','jing'],'怜见':['lian','jian'],'田边':['tian','bian'],'千典':['qian','dian']}

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
        for start,correct,difference,result in zip([4206,4211,4216,4221,4227],[0,1,0,1,1],[33,36,31,32,34],[167,131,100,68,34]):
            options=[self.rows[start+j]['translated_text'] for j in range(2)]
            self.assertEqual([j for j,n in enumerate(options) if all(x.endswith('ian') for x in SYLLABLES[n])],[correct])
            self.assertEqual([j for j,n in enumerate(options) if score(n)==difference],[correct])
            remaining-=score(options[correct]);self.assertEqual(remaining,result)
            # Verify the actual original bytecode: correct label takes continuation,
            # the alternative takes the common failure branch. No assumed menu order.
            loc=self.rows[start]['extra']['location'];command=self.commands[loc['instruction']]
            self.assertEqual(command['opcode'],106)
            targets=[a['value'] for a in command['args'] if a['kind']==4][:2]
            self.assertEqual(targets[correct],command['end'])
            self.assertEqual(targets[1-correct],15267)
        self.assertEqual(remaining-score('田边'),0)
        self.assertEqual(remaining-score('千典'),0)
        # The fifth victim also totals 34, but she is already dead.
        self.assertEqual(score('怜见'),34)
        self.assertIn('尚未遇害',self.texts[4965])

    def test_reveal_order_and_alias_given_name(self):
        first=''.join(self.texts[i] for i in [4175,4182,4185,4199,4203,4208,4213,4218,4223])
        for premature in ['200','差值','九键','手机']:
            self.assertNotIn(premature,first)
        self.assertIn('韵母都是ian',self.texts[4237])
        self.assertIn('千典',self.texts[6209])
        self.assertIn('名叫千典',self.texts[6224])
        self.assertEqual(''.join(self.rows[i]['translated_text'] for i in range(4310,4315)),
                         'QIANBIAN＝33QIANLIAN＝36BIANJIAN＝31JIANDIAN＝32LIANJIAN＝34')
        self.assertIn('7+4+2+6+3+4+2+6',self.texts[6216])

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
        for old in ['鱼吧','YUBA','９８２２','两位或三位数','译注','西野','优美子','玛雅','楢原','爱香','政隆','田中','a段','五十音','平假名','３２５８','sakanaya','tanaka','narahara','masataka','manaka','ha、ra']:
            self.assertNotIn(old,text)
        for ids in [[1416,1419,1422,1425],[2880,2883,2886,2889],[4412,4415,4418,4421]]:
            self.assertEqual([self.rows[i]['translated_text'].split('…')[1] for i in ids],['１６７','１３１','１００','６８'])
        self.assertTrue(self.rows[4424]['translated_text'].endswith('３４'))
        for r in self.rows.values():
            if r['translation_status']!=7 and r['extra']['location']['kind']=='script':
                self.assertLessEqual(len(r['translated_text'].encode('utf-16-le'))//2,20)

if __name__=='__main__':unittest.main()
