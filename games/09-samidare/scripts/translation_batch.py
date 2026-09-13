"""Split the ninth work's draft into per-script translation batches and apply them back.

The draft is one entry per display line, nameplate and menu label, keyed on
``(script, offset)``. A batch is a subset of one script, so a translator can work on
a chapter at a time; ``apply`` refuses anything that would not survive the pack
builder, so a batch that passes here cannot fail later with a budget error.

Only this module writes ``work/dialogue-tagged.json``. Parallel workers write batch
files and nothing else.
"""
import argparse
import json
import os
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
SERIES = WORK.parents[1]
sys.path.insert(0, str(SERIES / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'engine/adapters/gmode-20050117'))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'engine/adapters/gmode-v2'))
from project_config import resolve
import runtime_pack

PROJECT = resolve(project=WORK, allow_disabled=True)
DRAFT = WORK / 'work/dialogue-tagged.json'
BATCHES = WORK / 'work/parallel'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, data):
    path = Path(path).resolve()
    if not path.is_relative_to(WORK):
        raise ValueError('Output outside the ninth-game project')
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def shipped():
    """Every text-bearing unit as the pack builder sees it, with its real ceiling."""
    scripts = {}
    for path in sorted((WORK / 'raw').rglob('*.bin')):
        if path.name != 'scn0.bin':
            scripts[path.stem] = path.read_bytes()
    return runtime_pack.shipped_index(scripts)


def units():
    return load(DRAFT)['units']


def emphasis():
    path = WORK / 'work/emphasis.json'
    table = {}
    if path.is_file():
        for line in load(path)['lines']:
            table[(line['script'], line['offset'])] = line['runs']
    return table


def split(only=None, directory=BATCHES):
    emphasis_table = emphasis()
    # Nameplates and menu labels have no per-line budget of their own, so the draft
    # records 0 for them. Workers still need the ceiling they are held to, and that is
    # the longest string of the kind the game itself ever drew.
    ceilings = shipped()
    groups = {}
    for unit in units():
        groups.setdefault(unit['script'], []).append(unit)
    written = []
    for script in sorted(groups):
        if only and script not in only:
            continue
        batch = dict(
            script=script,
            note='One entry per display line. Fill target; len(target) must not exceed limit. '
                 'A unit that lists emphasis is drawn in several colours: give its target as runs, '
                 'one string per colour run, so the emphasis stays on the same content. '
                 'See work/STYLE_GUIDE.md.',
            units=[dict(offset=unit['offset'], kind=unit['kind'], source=unit['source'],
                        limit=unit['limit'] or ceilings[(script, unit['offset'])]['limit'],
                        fragments=unit['fragments'],
                        **({'emphasis': emphasis_table[(script, unit['offset'])]}
                           if (script, unit['offset']) in emphasis_table else {}),
                        **({'runs': unit['runs']} if unit.get('runs') else {}),
                        target=unit['target'])
                   for unit in groups[script]])
        path = Path(directory) / (script + '.src.json')
        save(path, batch)
        written.append((script, len(batch['units']), path))
    for script, count, path in written:
        print('%s: %d units -> %s' % (script, count, path.relative_to(WORK)))
    print('total %d units over %d scripts' % (sum(c for _, c, _ in written), len(written)))


def slice_batch(script, start, count, path):
    """Write a contiguous range of one script as its own batch, for parallel workers.

    The slice keeps the batch shape, so a worker's output file is applied verbatim.
    """
    batch = load(Path(BATCHES) / (script + '.src.json'))
    chosen = [unit for unit in batch['units'] if not unit['target']]
    window = chosen[start:start + count]
    if not window:
        raise ValueError('%s: no untranslated units at %d' % (script, start))
    out = Path(path)
    save(out, dict(script=script, note=batch['note'], units=window))
    print('%s: units %d-%d of %d untranslated -> %s'
          % (script, start, start + len(window) - 1, len(chosen), out.name))


def verify_path(batch_path):
    """Where the independent verification report for a batch lives.

    Translator batches are named ``<name>.trans.json`` and review repairs ``<name>.fixNN.json``;
    both take a sibling ``<name>.verify.json``.
    """
    name = Path(batch_path).name
    stem = name[: -len('.trans.json')] if name.endswith('.trans.json') else Path(name).stem
    return Path(batch_path).with_name(stem + '.verify.json')


def verify_slice(path, start, count, out):
    """Write source/target pairs for a verifier, who never sees the translator's claims.

    Verification is a different job from translation and has to be done by a reader who
    only compares the two texts, so the pair file carries the shipped source, the applied
    target and the colour runs, and nothing about how the translation was produced.
    """
    batch = load(path)
    rows = [unit for unit in batch['units']]
    by_key = {(unit['script'], unit['offset']): unit for unit in units()}
    colours = emphasis()
    pairs = []
    for unit in rows[start:start + count]:
        # A fix batch carries only offset and target, so the shipped kind, ceiling and
        # source come from the draft, which is also what the pack builder reads.
        applied = by_key[(batch['script'], unit['offset'])]
        # Verify what the batch proposes, not what the draft currently holds: a fix batch
        # is verified before it is allowed to replace the old text.
        proposed = unit.get('target') or applied['target']
        pairs.append(dict(offset=unit['offset'], kind=applied['kind'], limit=applied['limit'],
                          source=applied['source'], target=proposed,
                          **({'runs': unit.get('runs') or applied.get('runs')}
                             if (unit.get('runs') or applied.get('runs')) else {}),
                          **({'emphasis': colours[(batch['script'], unit['offset'])]}
                             if (batch['script'], unit['offset']) in colours else {})))
    if not pairs:
        raise ValueError('No pairs to verify in %s at %d' % (Path(path).name, start))
    destination = Path(out)
    save(destination, dict(
        script=batch['script'],
        batch=Path(path).name,
        note='Independent verification: for each entry decide whether ``target`` is the faithful '
             'rendering of ``source`` as its own display line. Report shifts, omissions, additions '
             'and mistranslations. An entry with ``emphasis`` is drawn in several colours: '
             '``emphasis`` is the source split and ``runs`` the Chinese split, index for index, and '
             'it is the run with a non-null colour that the game highlights. '
             'See work/parallel/VERIFIER_BRIEF.md.',
        units=pairs))
    print('%s: pairs %d-%d of %d -> %s'
          % (Path(path).name, start, start + len(pairs) - 1, len(rows), destination.name))


def require_verification(path, batch):
    """Refuse a batch that no independent reader has passed.

    The gate is deliberately blunt: a missing report, a failing verdict or a report that
    covers different offsets than the batch are all refusals. Translators assert counts
    and budgets; only this step asserts that each line says what its own line says.
    """
    report_path = verify_path(path)
    if not report_path.is_file():
        raise ValueError('%s has no independent verification report (%s)'
                         % (Path(path).name, report_path.name))
    report = load(report_path)
    if report.get('script') != batch['script']:
        raise ValueError('%s verification is for %r, not %r'
                         % (Path(path).name, report.get('script'), batch['script']))
    if report.get('verdict') != 'pass':
        raise ValueError('%s did not pass independent verification: %s'
                         % (Path(path).name, report.get('verdict') or 'no verdict'))
    expected = sorted(entry['offset'] for entry in batch['units'])
    covered = sorted(report.get('offsets') or [])
    if covered != expected:
        raise ValueError('%s verification covers %d offsets, the batch has %d'
                         % (Path(path).name, len(covered), len(expected)))
    return report


def validate(batch, index, emphasis_table):
    """Resolve a batch against the shipped index, rejecting anything unbuildable.

    A line drawn in more than one colour is only faithful if the translation says which
    of its characters the later colours cover, so those units must arrive as ``runs``:
    one string per colour run of the source, in order.
    """
    script = batch['script']
    resolved = []
    seen = set()
    for entry in batch['units']:
        offset = entry['offset']
        record = index.get((script, offset))
        if record is None:
            raise ValueError('%s: no text at %#x' % (script, offset))
        if offset in seen:
            raise ValueError('%s: duplicate offset %#x' % (script, offset))
        seen.add(offset)
        target = entry['target']
        if record['source'].strip() == '':
            # A blank display line is spacing, not text. Passing it through unchanged is
            # the faithful rendering, so it counts as done rather than as a gap.
            if target.strip() != '':
                raise ValueError('%s: blank line at %#x must stay blank' % (script, offset))
        else:
            if not target:
                raise ValueError('%s: empty target at %#x (%r)' % (script, offset, record['source']))
            if '\n' in target or target != target.strip():
                raise ValueError('%s: target has a newline or edge whitespace at %#x' % (script, offset))
        if len(target) > record['limit']:
            raise ValueError('%s: target %r is %d characters, the %s ceiling is %d, at %#x'
                             % (script, target, len(target), record['kind'], record['limit'], offset))
        runs = entry.get('runs')
        colours = emphasis_table.get((script, offset))
        if colours:
            if not runs:
                raise ValueError('%s: %#x is drawn in %d colours, so it needs runs'
                                 % (script, offset, len(colours)))
            if len(runs) != len(colours):
                raise ValueError('%s: %#x has %d colour runs but %d translated runs'
                                 % (script, offset, len(colours), len(runs)))
            if ''.join(runs) != target:
                raise ValueError('%s: the runs at %#x do not join into its target' % (script, offset))
        elif runs:
            raise ValueError('%s: %#x is a single colour, so it takes a plain target' % (script, offset))
        resolved.append((offset, target, runs))
    return resolved


def apply(paths):
    draft = load(DRAFT)
    index = shipped()
    emphasis_table = emphasis()
    by_key = {(unit['script'], unit['offset']): unit for unit in draft['units']}
    applied = 0
    for path in paths:
        batch = load(path)
        require_verification(path, batch)
        resolved = validate(batch, index, emphasis_table)
        for offset, target, runs in resolved:
            unit = by_key[(batch['script'], offset)]
            unit['target'] = target
            if runs:
                # Kept beside the target so the colour split survives re-extraction and
                # can be handed to the pack once the runtime draws per colour run.
                unit['runs'] = list(runs)
            else:
                unit.pop('runs', None)
            applied += 1
        print('%s: %d translations validated and applied' % (Path(path).name, len(resolved)))
    save(DRAFT, draft)
    refresh()
    return applied


def refresh():
    """Recompute the draft's translation counts in the project cache."""
    units_ = units()
    cache = load(WORK / 'work/cache.json')
    # The title lives in the series registry, so take it from there rather than letting
    # the cache keep a stale copy.
    cache['project_name'] = PROJECT['title']
    translated = sum(1 for unit in units_ if unit['target'])
    kinds = {}
    for unit in units_:
        kinds[unit['kind']] = kinds.get(unit['kind'], 0) + 1
    cache['extra'] = dict(
        translation_stage='source_extracted' if not translated else
                         ('translation_complete' if translated == len(units_) else 'translation_started'),
        coverage='%d display lines, %d nameplates and %d menu labels extracted to '
                 'work/dialogue-tagged.json; %d translated.' %
                 (kinds.get('line', 0), kinds.get('name', 0), kinds.get('choice', 0), translated),
        text=dict(draft='work/dialogue-tagged.json', units=len(units_), kinds=kinds,
                  translated=translated, renderings='texts/<script>.txt',
                  emphasis=len(load(WORK / 'work/emphasis.json')['lines'])))
    save(WORK / 'work/cache.json', cache)
    # ``status`` reads the extraction report, so keep its count truthful as well.
    report = WORK / 'reports/extraction.json'
    if report.is_file():
        extracted = load(report)
        extracted['text_translated'] = translated
        save(report, extracted)
    return translated


def check(strict=False):
    """Report coverage and every remaining budget or completeness problem."""
    draft = units()
    index = shipped()
    emphasis_table = emphasis()
    problems = []
    for unit in draft:
        record = index[(unit['script'], unit['offset'])]
        if unit['kind'] != record['kind'] or unit['source'] != record['source']:
            problems.append('%s:%#x draft entry no longer matches the shipped text'
                            % (unit['script'], unit['offset']))
        if unit['target'] and len(unit['target']) > record['limit']:
            problems.append('%s:%#x target is %d characters, ceiling %d'
                            % (unit['script'], unit['offset'], len(unit['target']), record['limit']))
        colours = emphasis_table.get((unit['script'], unit['offset']))
        if unit['target'] and colours:
            if len(unit.get('runs') or []) != len(colours):
                problems.append('%s:%#x is drawn in %d colours but has %d translated runs'
                                % (unit['script'], unit['offset'], len(colours),
                                   len(unit.get('runs') or [])))
            elif ''.join(unit['runs']) != unit['target']:
                problems.append('%s:%#x runs do not join into its target'
                                % (unit['script'], unit['offset']))
    translated = sum(1 for unit in draft if unit['target'])
    remaining = {}
    for unit in draft:
        if not unit['target']:
            remaining[unit['script']] = remaining.get(unit['script'], 0) + 1
    print('translated %d / %d' % (translated, len(draft)))
    print('remaining: %s' % (', '.join('%s=%d' % item for item in sorted(remaining.items())) or 'none'))
    print('problems: %d' % len(problems))
    for problem in problems[:20]:
        print('  ' + problem)
    if strict and (problems or remaining):
        raise SystemExit(1)
    return not problems and not remaining


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['split', 'slice', 'verify-slice', 'apply', 'check', 'status'])
    parser.add_argument('batch', nargs='*')
    parser.add_argument('--script', action='append')
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--from', dest='start', type=int, default=0)
    parser.add_argument('--count', type=int, default=0)
    parser.add_argument('--out', default=str(BATCHES))
    args = parser.parse_args()
    if args.action == 'split':
        split(only=set(args.script) if args.script else None, directory=Path(args.out))
    elif args.action == 'slice':
        if not args.script or not args.count:
            parser.error('slice needs --script and --count')
        slice_batch(args.script[0], args.start, args.count, args.out)
    elif args.action == 'verify-slice':
        if not args.batch or not args.count:
            parser.error('verify-slice needs a batch file and --count')
        verify_slice(args.batch[0], args.start, args.count, args.out)
    elif args.action == 'apply':
        if not args.batch:
            parser.error('apply needs at least one batch file')
        apply(args.batch)
    else:
        check(strict=args.strict)
