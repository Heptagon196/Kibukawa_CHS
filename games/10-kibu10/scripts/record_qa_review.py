"""Record the independently reviewed QA-fix delta over the scene baselines."""
import json

import pipeline as p
from apply_qa_fixes import INFO_LAYOUT_UNITS
from translation_review import candidates
from word_order_review import validate_review


def main():
    current=candidates()
    proof, changed = validate_review(current=current)

    integration=p.load(p.WORK/'work/fixes/integration-review.json')
    p.require(integration['validation']['all_current_targets_matched_active_units'], 'QA integration lacks stale-input proof')
    # The extra click/color record is file/help:2222. Its highlighted input
    # label was explicitly corrected from the obsolete mobile softkey wording
    # to the PC/controller controls after in-game user review.
    # Two scene-s10 clicks were re-read against their Japanese and following
    # navigation commands after the user flagged the disconnected transition.
    scene_s10 = {'scratch4.dat/s10:453:token21', 'scratch4.dat/s10:587:token5'}
    p.require(scene_s10 <= {u['id'] for u in changed['clicks']},
              'Missing reviewed scene-s10 transition')
    jugemu = {'scratch4.dat/s11:19254:token11', 'scratch4.dat/s11:19703:token11',
              'scratch4.dat/s11:19775:token11', 'scratch4.dat/s11:19884:token17'}
    p.require(jugemu <= {u['id'] for u in changed['clicks']},
              'Missing reviewed Jugemu quotation or translator note')
    identity = {'scratch4.dat/s01:8317:token21', 'scratch4.dat/s01:8739:token25'}
    p.require(identity <= {u['id'] for u in changed['clicks']}, 'Missing reviewed victim identity wording')
    document=dict(schema=1,adapter='gmode-20050817-direct',
        reviewer='root integration after independent semantic, punctuation, color, conflict and native INFO layout review; file/help:2222 controls, scene-s10 transition and s11 Jugemu quotation plus translator note, and s01 victim identity wording explicitly reviewed after user feedback',
        dialogue_sha256=p.sha((p.WORK/'work/dialogue-tagged.json').read_bytes()),
        integration_review='work/fixes/integration-review.json',
        integration_review_sha256=p.sha((p.WORK/'work/fixes/integration-review.json').read_bytes()),
        info_layout_units=sorted(INFO_LAYOUT_UNITS),
        clicks=changed['clicks'],colors=changed['colors'])
    document.update(proof)
    document['reviewer'] += '; exact word-order manifest and previous approval chain verified'
    p.save(p.WORK/'work/qa-fixes.reviewed.json',document)
    print(json.dumps({k:len(v) for k,v in changed.items()},ensure_ascii=False))


if __name__=='__main__': main()
