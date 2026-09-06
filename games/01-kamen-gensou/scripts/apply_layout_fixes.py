"""Apply reviewed layout wording fixes, retaining the original phonetic half-width forms."""
import re, shutil, unicodedata
import pipeline as p

cache=p.load(p.WORK/'work/cache.json')
by_id={x['text_index']:x for x in p.items(cache)}
updates={x['text_index']:x['translated_text'] for name in ('width_fixes_a.json','width_fixes_b.json') for x in p.load(p.WORK/'work'/name)}
updates.update({1648:"'ぼく'自称，",1649:"以'ひとろし'",2538:'叫玄马的公司任职，',3845:'正在玩'})
for index,item in by_id.items():
    if item['translation_status'] not in (1,2): continue
    target=updates.get(index,item['translated_text'])
    # Restore only phonetic strings actually present in the source, preserving
    # meaning and avoiding a global conversion of translated punctuation.
    for original in re.findall(r'\([\uff66-\uff9f]+(?: [\uff66-\uff9f]+)*\)',item['source_text']):
        normalized=unicodedata.normalize('NFKC',original[1:-1])
        target=target.replace('（'+normalized+'）',original).replace('('+normalized+')',original)
    if target != item['translated_text']: updates[index]=target
updates=[dict(text_index=i,translated_text=t) for i,t in sorted(updates.items()) if by_id[i]['translated_text']!=t]
batch_path=p.WORK/'work/layout_fixes_reviewed.json'; p.save(batch_path,updates)
p.apply_batch(batch_path)
actual=p.load(p.WORK/'work/cache.json'); by_id={x['text_index']:x for x in p.items(actual)}
for group,record in actual['files'].items():
    rows=[x for x in record['items'] if x['translation_status'] in (1,2)]
    if not rows: continue
    dest=p.inside(p.WORK/'translated_texts'/group); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text('\n'.join('[%s] %s'%(x['text_index'],x['translated_text']) for x in rows),encoding='utf-8')
sample_path=p.WORK/'work/sample_opening.json'
sample=p.load(sample_path)
shutil.copyfile(sample_path,p.inside(p.WORK/'work'/('sample_opening.json.bak.'+p.stamp())))
for row in sample: row['translated_text']=by_id[row['text_index']]['translated_text']
p.save(sample_path,sample)
p.save(p.WORK/'reports/layout_fixes.json',dict(changed_entries=len(updates),reason='User-reported overflow, source half-width readings and actual character-cell width',updates=updates))
