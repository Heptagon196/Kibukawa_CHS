"""Create contextual source/translation review packets without touching the cache."""
import collections
import pipeline as p

ROOT=p.WORK/'work/language_review'

def main():
    cache=p.load(p.WORK/'work/cache.json')
    manifest=p.load(p.WORK/'work/manifest.json')
    replay=p.load(p.WORK/'bepinex/build/replay.json')['commands']
    by_id={x['text_index']:x for x in p.items(cache)}
    slots={}
    for entry in manifest['entries']:
        loc=entry['location']
        if loc['kind']!='script': continue
        script=loc.get('member') or 'subscn_'+str(loc['part']+1)
        defs=manifest['definitions'][str(loc['opcode'])]
        slot=defs[:loc['argument']].count(3)
        slots[(script,loc['instruction'],slot)]=by_id[entry['text_index']]
    (ROOT/'input').mkdir(parents=True,exist_ok=True)
    (ROOT/'output').mkdir(exist_ok=True)
    p.save(ROOT/'baseline_cache.json',cache)
    groups=collections.defaultdict(list)
    for c in replay: groups[c['script']].append(c)
    for script,commands in groups.items():
        lines=[]; checked=[]; source=[]; target=[]; color='default'; default_color='default'
        def flush():
            if source:
                lines.append('整句(日): '+''.join(source)+'\n整句(中): '+''.join(target))
                source.clear();target.clear()
        for c in commands:
            op=c['opcode']
            if op==68: default_color='default('+str(c['integers'][0])+')';color=default_color
            if op==80: color='override('+str(c['integers'][0])+')'
            if op==81: color=default_color
            if op in (71,73,75,76,78,79) or op<25 or 105<=op<130:
                flush()
                lines.append(f"控制 @{c['instruction']} opcode={op} args={c['integers']}"+(' [点击等待]' if op in (76,78,79) else ''))
            for slot,(jp,zh) in enumerate(zip(c['strings'],c['expected'])):
                item=slots.get((script,c['instruction'],slot))
                if item is None: continue
                if item['translation_status'] in (1,2): checked.append(item['text_index'])
                lines.append(f"[{item['text_index']}] op={op} 色={color} 状态={item['translation_status']} 日={jp!r} 中={zh!r}")
                if op==72: source.append(jp or '');target.append(zh or '')
            if op==77: lines.append('[原文换行：中文由运行时重排]')
        flush()
        (ROOT/'input'/f'{script}.txt').write_text('\n'.join(lines),encoding='utf-8-sig')
        p.save(ROOT/'input'/f'{script}.indices.json',checked)
    non_script=[]
    for e in manifest['entries']:
        x=by_id[e['text_index']]
        if e['location']['kind']!='script' and x['translation_status'] in (1,2):
            non_script.append(dict(index=x['text_index'],source=x['source_text'],target=x['translated_text'],location=e['location']))
    p.save(ROOT/'input/non_script.json',non_script)
    p.save(ROOT/'coverage.json',dict(translated_indices=sorted(x['text_index'] for x in by_id.values() if x['translation_status'] in (1,2)),
                                   protected_indices=sorted(x['text_index'] for x in by_id.values() if x['translation_status']==7),
                                   baseline_sha256=p.sha((ROOT/'baseline_cache.json').read_bytes())))
    print('Prepared review packets for',len(groups),'scripts and',len(non_script),'UI/literal entries')

if __name__=='__main__': main()
