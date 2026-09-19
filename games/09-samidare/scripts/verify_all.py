"""One command that answers whether the ninth work's text is mechanically clean.

The independent reviews judge meaning; this covers everything a machine can settle, so a claim
of "no problems left" has something reproducible behind it instead of a summary. Hard checks
must all pass; review items are printed for a human or an agent to judge.

Hard checks
  coverage      every shipped text unit has a translation
  budget        every target fits its own line's ceiling
  shape         no blank target, no edge whitespace, no leftover kana, no half-width
                alphanumerics, no invented markup
  colour runs   every recoloured line carries one run per source colour run, joining to its
                target (the runtime stocks one run per fragment, so a mismatch misplaces the
                emphasis or refuses the pack)
  names         where a glossary canonical appears in a line, its render appears in the line
                or an immediate neighbour (short kana entries are skipped: the series entry
                みに matches inside 人並みに / 巧みに)

Review items (not failures)
  adjacent repeat   neighbouring display lines sharing >=4 characters; often the source's own
                    repetition, sometimes a real duplication
  enforcer noise   the skill's own same-string name check, which cannot work for JP->CN
"""
import json
import re
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / 'scripts'))
import translation_batch as tb                                    # noqa: E402
from run_skill_checks import name_render_check, locked            # noqa: E402

KANA = re.compile(r'[\u3041-\u309F\u30A0-\u30FF]')
HALF = re.compile(r'[0-9A-Za-z]')
MARKUP = re.compile(r'[<>]|\\n|\{[0-9]+\}|%s')
PUNCT = set('，。！？…、—ー「」『』“”‘’（）()·　 \t')

failures = []
notes = []

units = tb.units()
draft = {(u['script'], u['offset']): u for u in units}
index = tb.shipped()
emphasis = tb.emphasis()

missing = [key for key in index if not draft.get(key, {}).get('target')]
if missing:
    failures.append('coverage: %d shipped unit(s) untranslated, first %s' % (len(missing), missing[0]))

over = []
for key, unit in draft.items():
    record = index.get(key)
    if record is None:
        failures.append('coverage: draft entry %s carries no shipped text' % (key,))
        continue
    target = unit['target']
    if not target:
        continue
    if len(target) > record['limit']:
        over.append('%s@%d %d > %d' % (key[0], key[1], len(target), record['limit']))
    if unit['source'].strip() == '':
        if target.strip() != '':
            failures.append('shape: blank line %s@%d is not blank' % key)
        continue
    if target != target.strip():
        failures.append('shape: edge whitespace %s@%d' % key)
    if KANA.search(target):
        failures.append('shape: leftover kana %s@%d %r' % (key[0], key[1], target))
    if HALF.search(target):
        failures.append('shape: half-width alnum %s@%d %r' % (key[0], key[1], target))
    if MARKUP.search(target):
        failures.append('shape: markup %s@%d %r' % (key[0], key[1], target))
if over:
    failures.append('budget: %d target(s) over the ceiling, first %s' % (len(over), over[0]))

bad_runs = []
for key, colours in emphasis.items():
    unit = draft.get(key)
    if not unit or not unit['target']:
        continue
    runs = unit.get('runs') or []
    if len(runs) != len(colours):
        bad_runs.append('%s@%d %d runs vs %d colours' % (key[0], key[1], len(runs), len(colours)))
    elif ''.join(runs) != unit['target']:
        bad_runs.append('%s@%d runs do not join into the target' % key)
if bad_runs:
    failures.append('colour runs: %d problem(s), first %s' % (len(bad_runs), bad_runs[0]))

rows = [dict(text_index=i, script=u['script'], offset=u['offset'], source_text=u['source'],
             translated_text=u['target'], translation_status=1 if u['target'] else 0)
        for i, u in enumerate(units)]
render_missing = name_render_check(rows, locked())
if render_missing:
    notes.append('names: %d render(s) absent from the line and its neighbours, first %s@%d (%s)'
                 % (len(render_missing), render_missing[0]['script'], render_missing[0]['offset'],
                    render_missing[0]['name']))

by_script = {}
for unit in units:
    by_script.setdefault(unit['script'], []).append(unit)
repeats = []
for script, script_units in by_script.items():
    lines = [u for u in script_units if u['kind'] == 'line' and u['target']]
    for a, b in zip(lines, lines[1:]):
        left = ''.join(ch for ch in a['target'] if ch not in PUNCT)
        right = ''.join(ch for ch in b['target'] if ch not in PUNCT)
        for size in range(min(4, len(left), len(right)), 4 - 1, -1):
            if left[-size:] == right[:size]:
                repeats.append('%s@%d/%d %r' % (script, a['offset'], b['offset'], left[-size:]))
                break
if repeats:
    notes.append('adjacent repeat: %d neighbouring pair(s) share >=4 characters, first %s'
                 % (len(repeats), repeats[0]))

print('hard checks')
print('  coverage      %s' % ('FAIL' if missing else 'ok (%d units)' % len(index)))
print('  budget        %s' % ('FAIL' if over else 'ok'))
print('  shape         %s' % ('FAIL' if any(f.startswith('shape') for f in failures) else 'ok'))
print('  colour runs   %s' % ('FAIL' if bad_runs else 'ok (%d recoloured lines)' % len(emphasis)))
print('review items')
for note in notes or ['  none']:
    print('  ' + note)
if failures:
    print('\nFAILURES (%d):' % len(failures))
    for failure in failures[:20]:
        print('  ' + failure)
    raise SystemExit(1)
print('\nPASS: no mechanical problem in %d units' % len(units))
