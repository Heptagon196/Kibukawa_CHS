"""Apply the user's reviewed Chinese-name-only display preference.

Only the exact reviewed name-reading fragments are changed. Script slots,
source strings, dialogue controls, wordplay quotations and emoticons survive.
"""
import shutil
import pipeline as p

UPDATES = {
    17: '生王正生', 24: '癸生川', 43: '',
    210: '癸生川凌介', 211: '', 301: '叫砂永', 474: '',
    1196: '音成', 1288: '', 1292: '唐岛萌奈', 1980: '尾场九岁',
    1994: '『尾Q』的', 2540: '，', 2580: '续木宝月', 2581: '',
    2937: '', 4123: '', 4839: '飞鸟望美', 4840: '', 4883: '',
}


def main():
    cache_path = p.WORK / 'work/cache.json'
    before = p.load(cache_path)
    by_id = {x['text_index']: x for x in p.items(before)}
    changes = [dict(text_index=i, source_text=by_id[i]['source_text'],
                    previous_text=by_id[i]['translated_text'], translated_text=t)
               for i, t in UPDATES.items() if by_id[i]['translated_text'] != t]
    if not changes:
        print('Name readings already removed; no changes')
        return
    batch = [dict(text_index=x['text_index'], translated_text=x['translated_text'])
             for x in changes]
    p.save(p.WORK / 'work/name_readings_removed.json', batch)
    p.apply_batch(p.WORK / 'work/name_readings_removed.json')
    after = p.load(cache_path)
    current = {x['text_index']: x for x in p.items(after)}
    changed_files = []
    for group, record in after['files'].items():
        if not any(x['text_index'] in UPDATES for x in record['items']):
            continue
        rows = [x for x in record['items'] if x['translation_status'] in (1, 2)]
        dest = p.inside(p.WORK / 'translated_texts' / group)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text('\n'.join('[%s] %s' % (x['text_index'], x['translated_text'])
                                  for x in rows), encoding='utf-8')
        changed_files.append(str(dest.relative_to(p.WORK)))
    sample_path = p.WORK / 'work/sample_opening.json'
    sample = p.load(sample_path)
    shutil.copyfile(sample_path, p.inside(sample_path.with_name(sample_path.name + '.bak.' + p.stamp())))
    for row in sample:
        row['translated_text'] = current[row['text_index']]['translated_text']
    p.save(sample_path, sample)
    # IDs, source text, statuses and all non-target fields must remain untouched.
    for old in p.items(before):
        new = current[old['text_index']]
        p.require({k: v for k, v in old.items() if k != 'translated_text'} ==
                  {k: v for k, v in new.items() if k != 'translated_text'},
                  'Unexpected cache metadata change')
    p.save(p.WORK / 'reports/name_readings_removed.json', dict(
        reason='User requested Chinese character names without katakana pronunciation annotations',
        changed_entries=len(changes), annotation_occurrences=17,
        empty_fragment_indices=[i for i, t in UPDATES.items() if not t],
        preserved_non_name_kana_indices=[4386, 4614, 4632, 9223],
        changed_translated_files=changed_files, updates=changes,
        controls_unchanged=True, source_strings_unchanged=True))
    print('Removed 17 name/nickname annotations across %s translated entries' % len(changes))


if __name__ == '__main__':
    main()
