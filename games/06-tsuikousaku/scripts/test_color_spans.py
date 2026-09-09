"""Check semantic text enclosed by original color commands, without Unity UI."""
import unittest
import pipeline as p

def current_spans():
    cache=p.load(p.WORK/'work/cache.json')
    targets={}
    for group in cache['files'].values():
        for row in group['items']:
            loc=row['extra']['location']
            if loc['kind']=='script' and loc['opcode']==72:
                name=loc.get('member') or 'subscn_'+str(loc['part']+1)
                targets[(name,loc['instruction'])]=row['translated_text']
    spans={};current=None
    for command in p.load(p.WORK/'bepinex/build/replay.json')['commands']:
        key=(command['script'],command['instruction'])
        if command['opcode']==80:
            current=key;spans[key]=[command['integers'][0],'']
        elif command['opcode']==81:current=None
        elif current and current[0]==key[0] and command['opcode']==72:
            spans[current][1]+=targets.get(key,''.join(command['strings']))
    return spans

class ColorSpans(unittest.TestCase):
    def test_viewpoint_introduction(self):
        spans=current_spans()
        for address,color,text in [(29,2,'生王正生'),(72,6,'生王正生'),(89,5,'白鹭洲伊纲'),(111,2,'两个视角')]:
            with self.subTest(instruction=address):
                self.assertEqual(spans[('scn10',address)],[color,text])


    def test_all_reviewed_color_spans(self):
        spans=current_spans()
        reviewed=p.load(p.WORK/'research/color-spans.reviewed.json')
        self.assertEqual(len(spans),len(reviewed))
        for row in reviewed:
            with self.subTest(script=row['script'],start=row['start']):
                self.assertEqual(spans[(row['script'],row['start'])],[row['color'],row['target']])

    def test_tag_roundtrip_and_rejection(self):
        from tagged_dialogue import decode,markup
        layout=dict(script='fixture',end=90,groups=[
            dict(ids=[1],color=None),dict(ids=[2,3],color=5),dict(ids=[4],color=None)])
        text=markup(layout,['这是','白鹭洲伊纲','的记录'])
        result=decode(layout,text)
        self.assertEqual(''.join(result[i] for i in (2,3)),'白鹭洲伊纲')
        for broken in (text.replace('</color>',''),text.replace('color=RED','color=GREEN'),text.replace('<boundary=4/>',''),text+'<color=2>坏</color>'):
            with self.subTest(broken=broken),self.assertRaises(ValueError):decode(layout,broken)
        with self.assertRaises(ValueError):decode(layout,markup(layout,['字'*21,'白鹭洲伊纲','的记录']))

    def test_all_tagged_units_roundtrip(self):
        from tagged_dialogue import layouts,decode,markup,DOCUMENT
        from review_units import current
        commands,lookup=current()
        for layout,row in zip(layouts(commands,lookup),p.load(DOCUMENT)['units']):
            decoded=decode(layout,row['target'])
            text=markup(layout,[''.join(decoded[i] for i in g['ids']) for g in layout['groups']])
            self.assertEqual(text,row['target'])

    def test_dynamic_boundary_cannot_be_deleted(self):
        from tagged_dialogue import decode,markup
        layout=dict(script='fixture',end=90,groups=[dict(ids=[1],color=2),dict(ids=[2],color=2)])
        text=markup(layout,['共','次'])
        with self.assertRaises(ValueError):decode(layout,text.replace('</color><boundary=2/><color=YELLOW>',''))

if __name__=='__main__':unittest.main()

