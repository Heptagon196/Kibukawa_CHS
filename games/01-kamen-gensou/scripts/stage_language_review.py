"""Validate complete review coverage and stage proposals for the main review.

Does not write the live cache. Human/model language decisions remain necessary.
"""
import collections,copy
import pipeline as p

ROOT=p.WORK/'work/language_review'
TASKS=['language_scn0','language_scn1','language_scn2','language_scn3','language_scn45',
       'language_scn67','language_scn8_11','language_scn9','language_main']

def main():
    baseline=p.load(ROOT/'baseline_cache.json'); by_id={x['text_index']:x for x in p.items(baseline)}
    coverage=p.load(ROOT/'coverage.json'); checked=[]; proposals=[]; issues=[]; groups=collections.defaultdict(list)
    for task in TASKS:
        result=p.load(ROOT/'output'/f'{task}.json')
        ids=result['checked_indices']
        p.require(len(ids)==len(set(ids)),f'Duplicate coverage in {task}')
        p.require(all(i in by_id and by_id[i]['translation_status'] in (1,2) for i in ids),f'Invalid coverage in {task}')
        checked.extend(ids)
        for c in result['changes']:
            idx=c['text_index']; p.require(idx in ids,f'Change outside reviewed scope {task}:{idx}')
            p.require(c['before']==by_id[idx]['translated_text'],f'Stale proposal {task}:{idx}')
            p.require(c['translated_text']!=c['before'],f'Unchanged proposal {task}:{idx}')
            p.require(c.get('reason') and c.get('group'),f'Missing reason/group {task}:{idx}')
            proposal=dict(c,task=task);proposals.append(proposal);groups[task+'/'+c['group']].append(proposal)
        issues.extend(dict(x,task=task) for x in result.get('issues',[]))
    p.require(sorted(checked)==coverage['translated_indices'],'Review coverage is incomplete or duplicated')
    p.require(len({x['text_index'] for x in proposals})==len(proposals),'Conflicting changes')
    staged=copy.deepcopy(baseline); staged_by_id={x['text_index']:x for x in p.items(staged)}
    for c in proposals: staged_by_id[c['text_index']]['translated_text']=c['translated_text']
    p.validate_cache(staged,p.load(p.WORK/'work/manifest.json'))
    p.save(ROOT/'proposals.json',sorted(proposals,key=lambda x:x['text_index']))
    p.save(ROOT/'proposal_cache.json',staged)
    p.save(ROOT/'stage_report.json',dict(checked_count=len(checked),proposal_count=len(proposals),
        groups=len(groups),issues=issues,live_cache_modified=False))
    lines=[]
    for group,rows in groups.items():
        lines += ['\n## '+group,'索引 '+str([x['text_index'] for x in rows])]
        clusters=[]
        for idx in sorted(x['text_index'] for x in rows):
            if not clusters or idx-clusters[-1][-1]>4: clusters.append([])
            clusters[-1].append(idx)
        for cluster in clusters:
            context=[by_id[i] for i in sorted(by_id) if cluster[0]-2<=i<=cluster[-1]+2]
            lines += ['日：'+''.join(x['source_text'] for x in context),
                      '前：'+''.join(x['translated_text'] for x in context),
                      '后：'+''.join(staged_by_id[x['text_index']]['translated_text'] for x in context)]
        lines += ['理由：'+'；'.join(dict.fromkeys(x['reason'] for x in rows))]
    (ROOT/'proposal_review.txt').write_text('\n'.join(lines),encoding='utf-8-sig')
    print('Complete coverage:',len(checked),'proposals:',len(proposals),'groups:',len(groups),'issues:',len(issues))

if __name__=='__main__': main()
