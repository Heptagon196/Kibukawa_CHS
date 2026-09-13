"""Apply explicitly selected, coordinator-read review proposals to eighth-game batches.

This is not called by build or validation. It does not create review baselines.
"""
import argparse
from translation_io import WORK, load, save, check_target, digest


def apply(batch, rejected=()):
    path=WORK/'work/batches'/f'{batch:02d}.zh-CN.json'
    data=load(path)
    review=load(WORK/'work/reviews'/f'{batch:02d}.json')
    if set(review['reviewed_ids']) != {u['id'] for u in data['units']}:
        raise ValueError('Review does not cover complete batch')
    lookup={u['id']:u for u in data['units']}
    logpath=WORK/'work/review-decisions.json'
    log=load(logpath) if logpath.exists() else dict(schema=1,decisions=[])
    existing={d['id'] for d in log['decisions']}
    for proposal in review['findings']:
        key=proposal['id']
        if key in existing:
            continue
        unit=lookup[key]
        if key in rejected:
            log['decisions'].append(dict(id=key,batch=batch,decision='retain_current',reason=rejected[key]))
            continue
        if 'original_target' in proposal and proposal['original_target'] != unit['target'] and unit['target'] != proposal['suggested_target']:
            raise ValueError('Target changed since review: '+key)
        replacement=proposal['suggested_target']
        check_target(unit['source'],replacement)
        log['decisions'].append(dict(id=key,batch=batch,decision='accepted_after_coordinator_read',
            reason=proposal['reason'],source=unit['source'],before=unit['target'],after=replacement))
        unit['target']=replacement
        unit['review_note']=proposal['reason']
    save(path,data)
    save(logpath,log)
    return len(review['findings'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batches',nargs='+',type=int)
    args=parser.parse_args()
    for batch in args.batches:
        print(batch,apply(batch))
