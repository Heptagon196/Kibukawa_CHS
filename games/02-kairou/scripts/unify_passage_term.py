"""User-requested second-game terminology correction: 连廊 -> 连接通道."""
import time
import pipeline as p
import translation_batches as batches


def main():
    first_before=p.first_project_hashes()
    cache_path = p.WORK/'work/cache.json'
    cache = p.load(cache_path)
    drafts = {path:p.load(path) for path in batches.DRAFTS.glob('*.json')}
    changes = []
    for group in cache['files'].values():
        for row in group['items']:
            old = row.get('translated_text', '')
            if '连廊' not in old:
                continue
            new = old.replace('连廊', '连接通道')
            index = row['text_index']
            p.require(row['translation_status']==1, 'Unexpected translation status')
            p.require(len(new.encode('utf-16-le'))//2<=20, 'Text buffer overflow')
            matches = [draft for draft in drafts.values() if str(index) in draft['translations']]
            p.require(len(matches)==1 and matches[0]['translations'][str(index)]==old, 'Draft conflict: '+str(index))
            changes.append(dict(id=index,source=row['source_text'],before=old,after=new))
    if not changes:
        print('Passage terminology already unified.')
        return
    p.require(len(changes)==27, 'Unexpected passage revision count')
    p.save(p.WORK/'work/backups'/('cache-before-passage-term-'+str(time.time_ns())+'.json'), cache)
    by_id={r['text_index']:r for f in cache['files'].values() for r in f['items']}
    for change in changes:
        by_id[change['id']]['translated_text']=change['after']
        for draft in drafts.values():
            if str(change['id']) in draft['translations']:
                draft['translations'][str(change['id'])]=change['after']
    for path,draft in drafts.items():
        p.save(path,draft)
    p.save(cache_path,cache)
    glossary_path=p.WORK/'work/glossary.locked.json'
    glossary=p.load(glossary_path)
    glossary['second_game_policy']['passage_term']='渡り廊下／渡廊下统一译为连接通道；正文、菜单与平面图均不使用连廊简称。用户指定。'
    p.save(glossary_path,glossary)
    p.save(p.WORK/'reports/passage-term-revisions.json',dict(plugin_version='0.2.6',changes=changes))
    batches.merge()
    # The old translation audit's first-project snapshot predates the separately
    # authorized 1.0.31 reflow update. Verify this operation's own boundary.
    p.require(p.first_project_hashes()==first_before,'First game changed during terminology revision')
    print('Unified 27 passage references in second-game text and drafts.')


if __name__=='__main__':
    main()
