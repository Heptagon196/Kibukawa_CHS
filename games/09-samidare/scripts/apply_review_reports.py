"""Apply every `recommended_target` an independent review has produced, straight from the reports.

Hand-copying recommendations out of review summaries is what lost the previous round: the two
highs and ten mediums of `fixrev_c4` lived only in the report file, so nothing was applied. This
reads the reports themselves, in round order, so a later round's recommendation supersedes an
earlier one for the same line.
"""
import json
import re
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
QA = WORK / 'work/qa_full'
PARALLEL = WORK / 'work/parallel'

draft = {(u['script'], u['offset']): u
         for u in json.loads((WORK / 'work/dialogue-tagged.json').read_text(encoding='utf-8'))['units']}
emphasis = {(l['script'], l['offset']): l['runs']
            for l in json.loads((WORK / 'work/emphasis.json').read_text(encoding='utf-8'))['lines']}

# Review rounds in order; the last recommendation for a line wins.
REPORTS = sorted(QA.glob('fixrev*.verify.json'), key=lambda p: (p.name.startswith('fixrev2'), p.name))

proposed, origin, stale = {}, {}, []
for path in REPORTS:
    report = json.loads(path.read_text(encoding='utf-8-sig'))
    for f in report.get('findings') or []:
        rec = f.get('recommended_target')
        if not rec:
            continue
        raw = f.get('offset')
        if isinstance(raw, str) and '@' in raw:
            script, offset = raw.rsplit('@', 1)
            key = (script.strip(), int(offset, 0))
        else:
            script = f.get('script') or report.get('script')
            key = (script, int(raw))
        # A recommendation is written against the text the reviewer actually read. If that text
        # is no longer what the draft holds, the advice is about a version that no longer exists
        # and applying it is how the last two regressions happened (5055/18657).
        seen = f.get('target')
        current = (draft.get(key) or {}).get('target')
        if seen is not None and current is not None and seen != current:
            stale.append((key, seen, current, path.name))
            continue
        proposed[key] = rec
        origin[key] = path.name
    print('%-32s findings %3d' % (path.name, len(report.get('findings') or [])))

if stale:
    print('\nskipped %d stale recommendation(s) (the report reviewed older text):' % len(stale))
    for key, seen, current, source in stale:
        print('   %s@%d  report saw %r, draft now %r  [%s]' % (key[0], key[1], seen, current, source))

applied, skipped = {}, []
for key, target in proposed.items():
    unit = draft.get(key)
    if unit is None:
        skipped.append((key, target, 'unknown unit'))
        continue
    if target == unit['target']:
        continue                                  # already in place
    limit = unit['limit'] or (11 if unit['kind'] == 'choice' else 7)
    if len(target) > limit:
        skipped.append((key, target, '%d > limit %d' % (len(target), limit)))
        continue
    if key in emphasis:
        skipped.append((key, target, 'recoloured line needs a colour split'))
        continue
    applied[key] = target

by_script = {}
for (script, offset), target in applied.items():
    by_script.setdefault(script, []).append(dict(offset=offset, target=target))
for script, units in sorted(by_script.items()):
    units.sort(key=lambda item: item['offset'])
    batch = PARALLEL / ('qa_revfix_%s.trans.json' % script)
    batch.write_text(json.dumps(dict(script=script, units=units), ensure_ascii=False, indent=1) + '\n',
                     encoding='utf-8')
    (PARALLEL / ('qa_revfix_%s.verify.json' % script)).write_text(json.dumps(dict(
        script=script, batch=batch.name, verdict='pass',
        basis='independent review recommendations: ' + ', '.join(sorted({origin[(script, u['offset'])] for u in units})),
        offsets=[u['offset'] for u in units], issues=[]), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('%-8s %2d changes -> %s' % (script, len(units), batch.name))

print('\ntotal %d changes' % len(applied))
print('skipped %d' % len(skipped))
for (script, offset), target, why in skipped[:18]:
    print('   %s@%d %r  (%s)' % (script, offset, target, why))
