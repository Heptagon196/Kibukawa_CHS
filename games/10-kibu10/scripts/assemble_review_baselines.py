"""Combine independently reviewed records; never approve candidate output."""
import json
import pipeline as p
from translation_review import candidates


def main():
    current = candidates()
    outputs = {}
    reports = {}
    for kind, destination in [('clicks', 'work/click_boundaries.reviewed.json'),
                              ('colors', 'research/color-spans.reviewed.json')]:
        approved = {}
        provenance = []
        for batch in range(13):
            path = p.WORK / f'work/parallel/{batch:02d}.{kind}-reviewed.json'
            review = p.load(path)
            p.require(review.get('adapter') == 'gmode-20050817-direct', 'Wrong adapter: ' + str(path))
            p.require(review.get('reviewer'), 'Missing reviewer: ' + str(path))
            for record in review['units']:
                p.require(record['id'] not in approved, 'Duplicate approval: ' + record['id'])
                approved[record['id']] = record
            provenance.append(dict(batch=batch, reviewer=review['reviewer'],
                                   file=path.relative_to(p.WORK).as_posix(), sha256=p.sha(path.read_bytes())))
        changed = [r['id'] for r in current[kind] if approved.get(r['id']) != r]
        extra = sorted(set(approved) - {r['id'] for r in current[kind]})
        reports[kind] = dict(total=len(current[kind]), approved=len(approved), changed=changed, extra=extra)
        outputs[destination] = dict(schema=1, adapter='gmode-20050817-direct',
            reviewer='independent scene reviewers; root integration', provenance=provenance,
            units=[approved[r['id']] for r in current[kind] if r['id'] in approved])
    p.save(p.WORK / 'reports/review-integration.json', reports)
    print(json.dumps(reports, ensure_ascii=False))
    p.require(all(not r['changed'] and not r['extra'] for r in reports.values()),
              'Missing or stale independent approval; no baselines written')
    for path, document in outputs.items():
        p.save(p.WORK / path, document)


if __name__ == '__main__':
    main()
