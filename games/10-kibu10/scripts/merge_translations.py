"""Merge complete coordinator batches; source files and tagged shapes must agree."""
import json
import re
import pipeline as p


def main():
    document = p.load(p.WORK / 'work/dialogue-tagged.json')
    units = {u['id']: u for u in document['units']}
    merged, incomplete = [], []
    for batch in range(13):
        source = p.WORK / f'work/parallel/{batch:02d}.source.json'
        target = p.WORK / f'work/parallel/{batch:02d}.trans.json'
        if not target.exists():
            incomplete.append(batch)
            continue
        original = p.load(source)['units']
        translated = p.load(target)['targets']
        if set(translated) != {u['id'] for u in original}:
            incomplete.append(batch)
            continue
        for u in original:
            current = units[u['id']]
            p.require(current['source'] == u['source'], 'Stale batch: '+u['id'])
            value = translated[u['id']]
            p.require(isinstance(value, str) and value, 'Empty target: '+u['id'])
            p.require(re.findall('<[^>]+>', value) == re.findall('<[^>]+>', u['source']), 'Tag mismatch: '+u['id'])
            if current['target'] != value:
                current.update(target=value, translation_status='draft')
        merged.append(batch)
    for u in document['units']:
        if not u['active']:
            alias = 'file/' + u['id'].split('/', 1)[1]
            counterpart = units[alias]
            p.require(u['source'] == counterpart['source'], 'Non-identical backup copy: '+u['id'])
            u.update(target=counterpart['target'], translation_status='inactive_copy')
    p.save(p.WORK / 'work/dialogue-tagged.json', document)
    report = dict(merged_batches=merged, incomplete_batches=incomplete,
                  active_translated=sum(bool(u['target']) for u in document['units'] if u['active']),
                  semantic_review_complete=False)
    p.save(p.WORK / 'reports/batch-merge.json', report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
