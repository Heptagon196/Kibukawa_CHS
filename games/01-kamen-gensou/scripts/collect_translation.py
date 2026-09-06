"""Validate isolated agent outputs and stage one reviewed cache; never publish automatically."""
import collections, copy, re
import pipeline as p

def collect():
    tasks=p.load(p.WORK/'work/parallel/tasks.json')
    cache=copy.deepcopy(p.load(p.WORK/'work/cache.json'))
    by_id={x['text_index']:x for x in p.items(cache)}
    manifest=p.load(p.WORK/'work/manifest.json')
    results=[]; reviews=[]; line_groups=collections.defaultdict(list); absent=[]
    kana=[]; unchanged=[]; whitespace=[]
    for task in tasks:
        key=task['task']; file=p.WORK/f'work/parallel/output/{key}.json'
        if not file.exists(): absent.append(key); continue
        src=p.load(p.WORK/f'work/parallel/input/{key}.json'); dst=p.load(file)
        p.require([x['text_index'] for x in src]==[x['text_index'] for x in dst],f'Index mismatch: {key}')
        for s,t in zip(src,dst):
            i=s['text_index']; value=t['translated_text']
            p.require(isinstance(value,str),f'Nonstring translation {i}')
            if not s['source_text'].strip():
                whitespace.append(i); by_id[i]['translation_status']=7
                by_id[i]['extra']['note']='Source-only layout whitespace; preserved and excluded from translation.'
                continue
            p.require(value.strip(),f'Empty translation {i}')
            by_id[i].update(translated_text=value,translation_status=1)
            if s['display_line']: line_groups[s['display_line']].append((i,value))
            if re.search(r'[\u3040-\u30ff\uff66-\uff9f]',value): kana.append(dict(text_index=i,source=s['source_text'],translation=value))
            if value==s['source_text']: unchanged.append(dict(text_index=i,source=s['source_text']))
        review=p.WORK/f'work/parallel/output/{key}.review.json'
        if review.exists(): reviews.append(dict(task=key,issues=p.load(review)))
        results.append(dict(task=key,count=len(dst)))
    p.require(not absent,'Missing outputs: '+', '.join(absent))
    # Explicitly coordinated split boundaries and reviewed named contact.
    corrections={3956:'“原来如此，电脑',5904:'我开发的',5905:'系统并没有被',5906:'用在里面。'}
    for idx,text in corrections.items(): by_id[idx]['translated_text']=text
    # Apply separately reviewed corrections without editing individual agent artifacts.
    reviewed=p.WORK/'work/parallel/reviewed_corrections.json'
    if reviewed.exists():
        for item in p.load(reviewed): by_id[item['text_index']]['translated_text']=item['translated_text']
    sample=p.load(p.WORK/'work/sample_opening.json')
    p.require(all(by_id[x['text_index']]['translated_text']==x['translated_text'] for x in sample),'Approved sample changed')
    changes=p.validate_cache(cache,manifest)
    overflow=[]
    for line,rows in line_groups.items():
        size=sum(len(by_id[i]['translated_text'].encode('utf-16-le'))//2 for i,_ in rows)
        if size>20: overflow.append(dict(line=line,size=size,indices=[i for i,_ in rows]))
    p.require(not overflow,f'Line overflow: {overflow}')
    # Report the final reviewed text, not the uncorrected agent output.
    kana=[]; unchanged=[]
    for x in by_id.values():
        if x['translation_status'] not in (1,2): continue
        if re.search(r'[\u3040-\u30ff\uff66-\uff9f]',x['translated_text']):
            kana.append(dict(text_index=x['text_index'],source=x['source_text'],translation=x['translated_text']))
        if x['translated_text']==x['source_text']: unchanged.append(dict(text_index=x['text_index'],source=x['source_text']))
    p.save(p.WORK/'work/parallel/merged_cache.json',cache)
    report=dict(tasks=results,total_output=sum(x['count'] for x in results),translated=sum(x['translation_status'] in (1,2) for x in by_id.values()),
                excluded=sum(x['translation_status']==7 for x in by_id.values()),untranslated=sum(x['translation_status']==0 for x in by_id.values()),
                whitespace_excluded=whitespace,changed=len(changes),remaining_kana=kana,unchanged_text=unchanged,reviews=reviews,
                overflow=overflow,formal_cache_modified=False)
    p.save(p.WORK/'reports/translation_collection.json',report)
    print({k:report[k] for k in ('total_output','translated','excluded','untranslated','changed','whitespace_excluded')})
    print('Remaining kana:',len(kana),'Unchanged strings:',len(unchanged))

if __name__=='__main__': collect()
