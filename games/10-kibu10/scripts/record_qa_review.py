"""Record the independently reviewed QA-fix delta over the scene baselines."""
import json

import pipeline as p
from apply_qa_fixes import INFO_LAYOUT_UNITS
from translation_review import candidates


def main():
    current=candidates()
    changed={}
    for kind,path in [('clicks','work/click_boundaries.reviewed.json'),
                      ('colors','research/color-spans.reviewed.json')]:
        baseline={u['id']:u for u in p.load(p.WORK/path)['units']}
        changed[kind]=[u for u in current[kind] if baseline.get(u['id'])!=u]

    integration=p.load(p.WORK/'work/fixes/integration-review.json')
    p.require(integration['validation']['all_current_targets_matched_active_units'], 'QA integration lacks stale-input proof')
    p.require(len(changed['clicks'])==225+len(INFO_LAYOUT_UNITS) and len(changed['colors'])==20,
              'Unexpected semantic review delta: '+repr({k:len(v) for k,v in changed.items()}))
    document=dict(schema=1,adapter='gmode-20050817-direct',
        reviewer='root integration after independent semantic, punctuation, color, conflict and native INFO layout review',
        dialogue_sha256=p.sha((p.WORK/'work/dialogue-tagged.json').read_bytes()),
        integration_review='work/fixes/integration-review.json',
        integration_review_sha256=p.sha((p.WORK/'work/fixes/integration-review.json').read_bytes()),
        info_layout_units=sorted(INFO_LAYOUT_UNITS),
        clicks=changed['clicks'],colors=changed['colors'])
    p.save(p.WORK/'work/qa-fixes.reviewed.json',document)
    print(json.dumps({k:len(v) for k,v in changed.items()},ensure_ascii=False))


if __name__=='__main__': main()
