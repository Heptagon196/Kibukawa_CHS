"""Validate exact reviewed text transitions without writing approval or data files."""
import copy
import re

import pipeline as p

MANIFEST = 'work/word-order-review-20260922/integration-review.json'
PREVIOUS = 'work/word-order-review-20260922/previous-qa-fixes.reviewed.json'
INTEGRATION = 'work/fixes/integration-review.json'
ADAPTER = 'gmode-20050817-direct'
BASELINES = [('clicks', 'work/click_boundaries.reviewed.json'),
             ('colors', 'research/color-spans.reviewed.json')]


def indexed(rows, label):
    result = {}
    for row in rows:
        key = row['id']
        p.require(key not in result, 'Duplicate ' + label + ': ' + key)
        result[key] = row
    return result


def validate_review(document=None, current=None):
    """Reconstruct the approved input, verify its chain, then derive the exact delta.

    Input/output document fingerprints use canonical JSON, not platform newlines.
    The archived previous overlay and both review manifests use byte fingerprints.
    """
    from translation_review import candidates, digest

    document = p.load(p.WORK/'work/dialogue-tagged.json') if document is None else document
    review = p.load(p.WORK/MANIFEST)
    p.require(review.get('schema') == 1, 'Wrong word-order review schema')
    p.require(review.get('output_document_sha256') == digest(document),
              'Word-order output document differs from approved content')
    units = indexed(document['units'], 'document unit')
    active = {key for key, unit in units.items() if unit['active']}
    reviewed = review['reviewed_ids']
    p.require(len(reviewed) == len(set(reviewed)) and set(reviewed) == active,
              'Word-order reviewed IDs must match all active units exactly')

    before = copy.deepcopy(document)
    old_units = indexed(before['units'], 'previous unit')
    changes = indexed(review['changes'], 'word-order change')
    p.require(bool(changes), 'Word-order review has no exact changes')
    for key, change in changes.items():
        p.require(key in active, 'Word-order change is not active: ' + key)
        unit = units[key]
        p.require(unit['source'] == change['source'], 'Stale word-order source: ' + key)
        p.require(unit['target'] == change['target'], 'Unapproved word-order target: ' + key)
        p.require(isinstance(change['old_target'], str) and bool(change['target']) and
                  change['old_target'] != change['target'], 'Invalid word-order transition: ' + key)
        p.require(bool(change.get('reason')) and bool(change.get('proposal_file')),
                  'Missing word-order review provenance: ' + key)
        tags = re.findall(r'<[^>]+>', unit['source'])
        p.require(tags == re.findall(r'<[^>]+>', change['old_target']) ==
                  re.findall(r'<[^>]+>', change['target']), 'Word-order tag mismatch: ' + key)
        old_units[key]['target'] = change['old_target']
    p.require(review.get('input_document_sha256') == digest(before),
              'Word-order input reconstruction differs from approved content')
    p.require({u['id'] for u in before['units'] if u['active']} == active,
              'Word-order active IDs changed')

    p.require(review.get('previous_overlay') == PREVIOUS, 'Unexpected previous review path')
    previous_path = p.WORK/PREVIOUS
    p.require(review.get('previous_overlay_sha256') == p.sha(previous_path.read_bytes()),
              'Previous QA review archive changed')
    previous = p.load(previous_path)
    p.require(previous.get('adapter') == ADAPTER and previous.get('schema') == 1,
              'Invalid previous QA review')
    p.require(previous.get('integration_review') == INTEGRATION and
              previous.get('integration_review_sha256') == p.sha((p.WORK/INTEGRATION).read_bytes()),
              'Previous QA integration review changed')

    old_candidates = candidates(before)
    actual_candidates = candidates(document)
    if current is not None:
        p.require(current == actual_candidates, 'Stale current review candidates')
    delta = {}
    for kind, path in BASELINES:
        baseline = p.load(p.WORK/path)
        p.require(baseline.get('adapter') == ADAPTER, 'Invalid review baseline: ' + kind)
        base = indexed(baseline['units'], kind + ' baseline')
        old = indexed(old_candidates[kind], kind + ' previous candidate')
        new = indexed(actual_candidates[kind], kind + ' current candidate')
        overlay = indexed(previous[kind], kind + ' previous approval')
        p.require(set(overlay) <= set(old), 'Unknown previous QA records: ' + kind)
        approved = dict(base)
        approved.update(overlay)
        p.require(approved == old, 'Previous document is not exactly approved: ' + kind)
        p.require(set(old) == set(new), 'Word-order candidate IDs changed: ' + kind)
        # The output was already proven to differ only by the manifest's exact
        # targets. Derive the cumulative overlay, preserving previous approvals.
        delta[kind] = [row for row in actual_candidates[kind] if base.get(row['id']) != row]

    proof = dict(word_order_review=MANIFEST,
                 word_order_review_sha256=p.sha((p.WORK/MANIFEST).read_bytes()),
                 input_document_sha256=review['input_document_sha256'],
                 output_document_sha256=review['output_document_sha256'],
                 previous_overlay=PREVIOUS,
                 previous_overlay_sha256=review['previous_overlay_sha256'])
    return proof, delta
