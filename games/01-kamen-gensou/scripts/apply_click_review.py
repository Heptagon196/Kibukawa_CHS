"""One-time application of the 1.0.20 source/target click-boundary review."""
import pipeline as p
from check_click_boundaries import units, BASELINE

def main():
    updates={x['text_index']:x['translated_text'] for x in p.load(p.WORK/'work/wait_boundary_fixes.json')}
    reviews=[p.load(p.WORK/f'work/wait_review_{part}.json') for part in ('early','middle','late')]
    for review in reviews:
        for finding in review['findings']:
            updates.update({int(k):v for k,v in finding.get('suggested',{}).items()})
            updates.update({x['text_index']:x['translated_text'] for x in finding.get('changes',[])})
    updates.update({x['text_index']:x['translated_text'] for x in p.load(p.WORK/'work/click_review_width_followup.json')})
    cache=p.load(p.WORK/'work/cache.json')
    changes=[dict(text_index=x['text_index'],before=x['translated_text'],translated_text=updates[x['text_index']])
             for x in p.items(cache) if x['text_index'] in updates and x['translated_text']!=updates[x['text_index']]]
    path=p.WORK/'work/click_review_fixes.json';p.save(path,changes);p.apply_batch(path)
    cache=p.load(p.WORK/'work/cache.json')
    for group,f in cache['files'].items():
        rows=[x for x in f['items'] if x['translation_status'] in (1,2)]
        if rows:(p.WORK/'translated_texts'/group).write_text('\n'.join('[%s] %s'%(x['text_index'],x['translated_text']) for x in rows),encoding='utf-8')
    # Use original command structure, substituting the reviewed final cache values.
    replay=p.load(p.WORK/'bepinex/build/replay.json')['commands']
    targets={}
    by_id={x['text_index']:x for x in p.items(cache)}
    for entry in p.load(p.WORK/'work/manifest.json')['entries']:
        x=by_id[entry['text_index']]
        loc=entry['location']
        if loc['kind']=='script' and loc['opcode']==72:
            name=loc.get('member') or 'subscn_'+str(loc['part']+1)
            targets[(name,loc['instruction'])]=x['translated_text']
    for c in replay:
        if c['opcode']==72 and (c['script'],c['instruction']) in targets:
            c['expected']=[targets[c['script'],c['instruction']]]
    p.save(BASELINE,dict(version='1.0.20',review_reports=['wait_review_'+x+'.json' for x in ('early','middle','late')],units=units(replay)))
    p.save(p.WORK/'reports/click_boundary_review.json',dict(version='1.0.20',reviews=reviews,changes=changes,
        initial_fix=p.load(p.WORK/'work/wait_boundary_fixes.json'),
        limitation='Static source/target review and coroutine replay; user performs in-game verification.'))
    readme=p.WORK/'README.md'
    text=readme.read_text(encoding='utf-8').replace('当前插件为 1.0.19。','当前插件为 1.0.20。已按原始点击边界对照全篇译文，修复跨等待指令的句首/连接词错位，并在构建中锁定审校后的点击单元；详见 reports/click_boundary_review.json。')
    text=text.replace('米妮与美贰的同音解释移到角色话语之外的括号译注。音成自我介绍的谐音解释移至角色台词外的括号译注。','')
    readme.write_text(text,encoding='utf-8')
    print('Applied',len(changes),'additional slot changes; reviewed baseline units:',len(units(replay)))

if __name__=='__main__':main()
