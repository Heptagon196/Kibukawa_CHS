"""Recorded 0.2.1 menu-only revisions for the original four-glyph columns."""
import time
import pipeline as p
import translation_batches as batches

REVISIONS = {
    13: ('最终章后半', '最终后半'),
    3170: ('斋树的房间', '斋树房间'),
    3237: ('斋树的房间', '斋树房间'),
    3418: ('不在场证明', '不在场证'),
    3606: ('不在场证明', '不在场证'),
    3905: ('不在场证明', '不在场证'),
    3806: ('查看房间分配', '房间分配'),
    4654: ('萨纳米建设', '萨纳米'),
}


def main():
    cache_path = p.WORK/'work/cache.json'
    cache = p.load(cache_path)
    rows = {x['text_index']: x for group in cache['files'].values() for x in group['items']}
    drafts = {path: p.load(path) for path in batches.DRAFTS.glob('*.json')}
    for index, (old, new) in REVISIONS.items():
        p.require(rows[index]['translated_text'] in (old, new), 'Later menu revision exists: '+str(index))
        p.require(105 <= rows[index]['extra']['location']['opcode'] < 130, 'Expected a menu slot')
    p.save(p.WORK/'work/backups'/('cache-before-menu-fit-'+str(time.time_ns())+'.json'), cache)
    changes = []
    for index, (old, new) in REVISIONS.items():
        rows[index]['translated_text'] = new
        for draft in drafts.values():
            if str(index) in draft['translations']:
                p.require(draft['translations'][str(index)] in (old, new), 'Draft revision conflict')
                draft['translations'][str(index)] = new
        changes.append(dict(id=index, source=rows[index]['source_text'], before=old, after=new,
                            reason='Original two-column menu supports four full-width glyphs per option'))
    for path, draft in drafts.items():
        p.save(path, draft)
    p.save(cache_path, cache)
    p.save(p.WORK/'reports/menu-label-revisions.json', dict(plugin_version='0.2.1', changes=changes))
    glossary_path = p.WORK/'work/glossary.locked.json'
    glossary = p.load(glossary_path)
    glossary['interface_short_forms'] = {old: new for old, new in REVISIONS.values()}
    p.save(glossary_path, glossary)
    batches.merge()


if __name__ == '__main__':
    main()
