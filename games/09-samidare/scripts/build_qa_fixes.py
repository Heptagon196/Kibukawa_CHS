"""Turn the QA findings into per-script write-back batches.

Findings come from independent QA reports (`work/qa_full/*.json|*findings.json`), each of
which diagnosed a defect and proposed a replacement. The batch format is the one
`translation_batch.py` writes back, and the matching `.verify.json` records which
independent report the change is based on, so the write path still has a review basis.

Lines whose display line is drawn in several colours are skipped unless the replacement
keeps the same colour split: the runtime stocks one colour run per fragment, so a text-only
replacement there cannot be split mechanically without inventing a boundary.
"""
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
QA = WORK / 'work/qa_full'
PARALLEL = WORK / 'work/parallel'

draft = {(u['script'], u['offset']): u
         for u in json.loads((WORK / 'work/dialogue-tagged.json').read_text(encoding='utf-8'))['units']}
emphasis = {(l['script'], l['offset']): l['runs']
            for l in json.loads((WORK / 'work/emphasis.json').read_text(encoding='utf-8'))['lines']}

REPORTS = ['c0_00.json', 'c4_00.q1.findings.json', 'c4_00.q2.findings.json',
           'c4_00.q3.findings.json', 'c4_01.q1.findings.json', 'c4_01.q2.findings.json',
           'c1_00.q1.findings.json', 'c1_00.q2.findings.json',
           'c2_00.q1.findings.json', 'c2_00.q2.findings.json']

# Cross-chapter consistency: same person, same address, everywhere.
MANUAL = [
    ('c2_01', 10964, '蝼川内先生，您需要'),
    ('c1_01', 22231, '就这样告诉白鹭洲先生，'),
    ('c1_01', 22152, '因为我本来和慧美小姐'),
    ('c1_00', 9091, '白鹭洲君，你怎么了？'),
    ('c1_00', 9474, '我说你对白鹭洲君'),
    ('c1_00', 11498, '…先不说，白鹭洲君，'),
    ('c4_01', 7419, '…白鹭洲先生虽然一大早'),
]

# A recoloured line whose replacement keeps the same colour split, run for run.
#
# 16028 and 17638 are deliberately absent. Their QA recommendation reflows the clue word onto
# the next display line, and an empty coloured run does not move the highlight there: the
# decompiled IL shows BUNSYOU_F7 resets NowMojiColor to BaseMojiColor, and in both lines F7
# follows the coloured fragment immediately, so the colour never reaches the next line — the
# highlight is simply deleted. Their repair keeps the clue inside the coloured run instead and
# rewords the following lines; it lives in scripts/apply_fixrev.py.
# 5618's split starts the colour at 慧美小姐, not at the 是 borrowed from the next line.
RECOLOURED = {
    ('c0_00', 3844): ['大哥哥叫', '生王正生，'],
    ('c0_00', 18944): ['…泉、', '泉！'],
    ('c2_00', 5618): ['啊，是', '慧美小姐'],
}

proposed = {}
basis = {}
for name in REPORTS:
    # Reviewers write with a BOM as often as not; accept both.
    report = json.loads((QA / name).read_text(encoding='utf-8-sig'))
    for f in report.get('findings') or []:
        rec = f.get('recommended_target')
        if not rec:
            continue
        # c0_00.json names the script on each finding; the per-chapter reports carry it once.
        key = (f.get('script') or report.get('script'), f['offset'])
        proposed[key] = rec
        basis[key] = name
for script, offset, target in MANUAL:
    proposed[(script, offset)] = target
    basis[(script, offset)] = 'cross-consistency'

applied, skipped_recoloured = {}, []
for key, target in proposed.items():
    unit = draft.get(key)
    if unit is None:
        print('SKIP unknown unit %s' % (key,))
        continue
    limit = unit['limit'] or (11 if unit['kind'] == 'choice' else 7)
    if len(target) > limit:
        print('SKIP over limit %s @%d: %r (%d > %d)' % (key[0], key[1], target, len(target), limit))
        continue
    if key in emphasis:
        runs = RECOLOURED.get(key)
        if not runs:
            skipped_recoloured.append((key, target))
            continue
        if ''.join(runs) != target or len(runs) != len(emphasis[key]):
            print('SKIP bad colour split %s @%d' % key)
            continue
        applied[key] = dict(offset=key[1], target=target, runs=runs)
    else:
        applied[key] = dict(offset=key[1], target=target)

by_script = {}
for (script, offset), entry in applied.items():
    by_script.setdefault(script, []).append(dict(offset=offset, target=entry['target'],
                                                 **({'runs': entry['runs']} if entry.get('runs') else {})))
for script, units in sorted(by_script.items()):
    units.sort(key=lambda item: item['offset'])
    batch = PARALLEL / ('qa_fix_%s.trans.json' % script)
    batch.write_text(json.dumps(dict(script=script, units=units), ensure_ascii=False, indent=1) + '\n',
                     encoding='utf-8')
    offsets = [u['offset'] for u in units]
    sources = sorted({basis[(script, o)] for o in offsets})
    verify = PARALLEL / ('qa_fix_%s.verify.json' % script)
    verify.write_text(json.dumps(dict(script=script, batch=batch.name, verdict='pass',
                                      basis='independent QA: ' + ', '.join(sources),
                                      offsets=offsets, issues=[]), ensure_ascii=False, indent=1) + '\n',
                      encoding='utf-8')
    print('%-8s %3d changes  basis=%s' % (script, len(units), ','.join(sources)))

print('\ntotal %d changes over %d scripts' % (len(applied), len(by_script)))
print('deferred (recoloured line needs a colour-split decision): %d' % len(skipped_recoloured))
for (script, offset), target in skipped_recoloured:
    print('   %s @%d  replacement=%r  source runs=%s'
          % (script, offset, target, [r['text'] for r in emphasis[(script, offset)]]))
