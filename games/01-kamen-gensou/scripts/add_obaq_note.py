"""Add the requested nickname note inside its existing click unit."""
import pipeline as p

def main():
    text='人称『尾Q』。（译注：日语中Q与九同音，尾Q也与Q太郎简称同音；尾场和Q太郎都怕狗。）'
    p.require(len(text)<=60,'Note exceeds the three existing text slots')
    changes=[dict(text_index=1993+i,translated_text=text[i*20:(i+1)*20]) for i in range(3)]
    path=p.WORK/'work/obaq_note_fixes.json';p.save(path,changes);p.apply_batch(path)
    cache=p.load(p.WORK/'work/cache.json')
    rows=cache['files']['scn2.txt']['items']
    (p.WORK/'translated_texts/scn2.txt').write_text('\n'.join('[%s] %s'%(x['text_index'],x['translated_text']) for x in rows if x['translation_status'] in (1,2)),encoding='utf-8')
    baseline=p.load(p.WORK/'work/click_boundaries.reviewed.json')
    found=[u for u in baseline['units'] if u['script']=='scn2' and u['end']==14350]
    p.require(len(found)==1,'Nickname click unit missing')
    before=found[0]['target'];found[0]['target']=''.join(x['translated_text'] for x in changes)
    baseline['version']='1.0.27';p.save(p.WORK/'work/click_boundaries.reviewed.json',baseline)
    glossary=p.load(p.WORK/'work/glossary.locked.json')
    for term in glossary['terms']:
        if term['src']=='オバキュー':term['note']='首次介绍时说明三层联系：日语中Q与九同音，尾Q与《Q太郎》的日语简称同音，尾场和Q太郎都怕狗。不写具体读音，不使用指代不清的“两者”，后续称呼不重复译注。'
    p.save(p.WORK/'work/glossary.locked.json',glossary)
    p.save(p.WORK/'reports/obaq_note_review.json',dict(before=before,after=found[0]['target'],changes=changes,
        original_wait_instruction=14350,note_only_at_first_introduction=True))
    readme=p.WORK/'README.md';readme.write_text(readme.read_text(encoding='utf-8').replace('当前插件为 1.0.26。','当前插件为 1.0.27。尾Q译注完整说明Q与九、Q太郎简称的谐音及共同怕狗的特点。'),encoding='utf-8')

if __name__=='__main__':main()
