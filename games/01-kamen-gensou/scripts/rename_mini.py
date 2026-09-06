"""Use the user-approved name pair 美妮 / 米妮 and remove its translation note."""
import json
import pipeline as p

cache=p.load(p.WORK/'work/cache.json')
updates={x['text_index']:x['translated_text'].replace('美贰','美妮')
         for x in p.items(cache) if x['translation_status'] in (1,2) and '美贰' in x['translated_text']}
updates.update({4886:'“米妮！？”',5002:'我从没',5003:'怀疑过。”'})
changes=[dict(text_index=x['text_index'],before=x['translated_text'],translated_text=updates[x['text_index']],
              reason='用户指定本名美妮、网名米妮；删除该名字的译注与额外读音标注，保持人物及账号区别。')
         for x in p.items(cache) if x['text_index'] in updates and x['translated_text']!=updates[x['text_index']]]
path=p.WORK/'work/meini_name_fixes.json';p.save(path,changes);p.apply_batch(path)
actual=p.load(p.WORK/'work/cache.json')
p.require(not any('美贰' in x['translated_text'] for x in p.items(actual)), 'Old translated name remains')
for group,f in actual['files'].items():
    rows=[x for x in f['items'] if x['translation_status'] in (1,2)]
    if rows:(p.WORK/'translated_texts'/group).write_text('\n'.join('[%s] %s'%(x['text_index'],x['translated_text']) for x in rows),encoding='utf-8')
path=p.WORK/'work/glossary.locked.json'
glossary=json.loads(json.dumps(p.load(path),ensure_ascii=False).replace('美贰','美妮'))
glossary['chinese_only_clue_rendering']['みに']='用户指定：网名米妮、本名美妮（全名狭川美妮），中文近音但声调不同；不加日语同音译注或mini注音。人物与账号保持区别。'
def revise(value):
    if isinstance(value,dict):
        if isinstance(value.get('decision'),str) and '需注明谐音' in value['decision']:
            value['decision']=value['decision'].replace('需注明谐音','采用用户指定的中文近音对应，不加该姓名的译注')
        for child in value.values():revise(child)
    elif isinstance(value,list):
        for child in value:revise(child)
revise(glossary);p.save(path,glossary)
p.save(p.WORK/'reports/meini_name_review.json',dict(changes=changes,old_name_remaining=0,source_keys_unchanged=True))
print('Updated',len(changes),'text slots; surname/name and account identity preserved.')
