"""Apply the user-approved private mail pronoun without moving click boundaries."""
import pipeline as p

def main():
    cache=p.load(p.WORK/'work/cache.json')
    changes=[dict(text_index=x['text_index'],before=x['translated_text'],translated_text=x['translated_text'].replace('小生','在下'))
             for x in p.items(cache) if '小生' in x['translated_text']]
    path=p.WORK/'work/mail_pronoun_fixes.json';p.save(path,changes);p.apply_batch(path)
    cache=p.load(p.WORK/'work/cache.json')
    p.require(not any('小生' in x['translated_text'] for x in p.items(cache)),'Old pronoun remains')
    rows=cache['files']['scn2.txt']['items']
    (p.WORK/'translated_texts/scn2.txt').write_text('\n'.join('[%s] %s'%(x['text_index'],x['translated_text']) for x in rows if x['translation_status'] in (1,2)),encoding='utf-8')
    glossary=p.load(p.WORK/'work/glossary.locked.json')
    glossary['chinese_only_clue_rendering']['ぼく']='在下（用户指定，邮件私密自称的中文功能性对应）'
    p.save(p.WORK/'work/glossary.locked.json',glossary)
    baseline=p.load(p.WORK/'work/click_boundaries.reviewed.json')
    for unit in baseline['units']:unit['target']=unit['target'].replace('小生','在下')
    baseline['version']='1.0.24'
    p.save(p.WORK/'work/click_boundaries.reviewed.json',baseline)
    guide=p.WORK/'work/STYLE_GUIDE.md';guide.write_text(guide.read_text(encoding='utf-8').replace('ぼく对应小生','ぼく按用户指定对应在下'),encoding='utf-8')
    readme=p.WORK/'README.md';readme.write_text(readme.read_text(encoding='utf-8').replace('当前插件为 1.0.23。','当前插件为 1.0.24。邮件特殊自称按用户指定统一为“在下”，相关线索说明同步更新。'),encoding='utf-8')
    p.save(p.WORK/'reports/mail_pronoun_review.json',dict(changes=changes,old_pronoun_remaining=0,click_boundaries_preserved=True))
    print('Updated',len(changes),'mail-pronoun slots.')

if __name__=='__main__':main()
