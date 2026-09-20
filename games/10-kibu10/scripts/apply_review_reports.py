"""Apply selected, coordinator-accepted exact review fixes with stale-input guards."""
import argparse
import re
import pipeline as p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batches', nargs='+', type=int)
    args = parser.parse_args()
    for batch in args.batches:
        folder = p.WORK / 'work/parallel'
        source = {u['id']:u for u in p.load(folder/f'{batch:02d}.source.json')['units']}
        review = p.load(folder/f'{batch:02d}.review.json')
        path = folder/f'{batch:02d}.trans.json'
        draft = p.load(path)
        fixes = []
        for finding in review['findings']:
            key, value = finding['id'], finding['suggested_target']
            p.require(source[key]['source'] == finding['source'], 'Stale review source: '+key)
            p.require(draft['targets'][key] in (finding['target'], value), 'Stale review target: '+key)
            p.require(re.findall('<[^>]+>',value)==re.findall('<[^>]+>',source[key]['source']), 'Bad review tags: '+key)
            p.require(bool(value), 'Empty review target: '+key)
            draft['targets'][key] = value
            fixes.append(dict(id=key, before=finding['target'], after=value, reason=finding['issue']))
        p.save(path, draft)
        p.save(folder/f'{batch:02d}.applied-review.json',dict(batch=batch,reviewer=review['reviewer'],
            coordinator='root', status='applied_awaiting_recheck', fixes=fixes))
        print(batch, len(fixes))


if __name__=='__main__':
    main()
