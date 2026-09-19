"""Audit every ninth-title dialogue colour span against the translated draft.

The source VM carries colour state across display lines. ``BUNSYOU_IRO`` starts an
override and ``BUNSYOU_F7`` either closes ruby or restores the base colour.  This
report therefore includes both mixed-colour lines and whole lines that inherit a
non-base colour; checking only draft entries with ``runs`` misses the latter.
"""
import argparse
import json
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
ROOT = WORK.parents[1]
sys.path.insert(0, str(ROOT / 'engine/adapters/gmode-20050117'))
from runtime_pack import colour_lines
from vm import parse_bin


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def scripts():
    return {path.stem: path.read_bytes()
            for path in sorted((WORK / 'raw').rglob('*.bin'))
            if path.name != 'scn0.bin'}


def audit():
    units = load(WORK / 'work/dialogue-tagged.json')['units']
    by_key = {(unit['script'], unit['offset']): unit for unit in units}
    by_script = {}
    for unit in units:
        if unit.get('kind', 'line') == 'line':
            by_script.setdefault(unit['script'], []).append(unit)
    positions = {key: index for script, rows in by_script.items()
                 for index, unit in enumerate(rows) for key in [(script, unit['offset'])]}

    records = []
    counts = dict(total_lines=0, plain=0, whole_colour=0, mixed_colour=0,
                  structurally_valid=0, structural_errors=0)
    for script, raw in scripts().items():
        lines = colour_lines(parse_bin(raw))
        counts['total_lines'] += len(lines)
        for offset, source_runs in lines.items():
            colours = [run['colour'] for run in source_runs]
            coloured = any(colour is not None for colour in colours)
            mixed = len(source_runs) > 1
            if not coloured:
                counts['plain'] += 1
            elif mixed:
                counts['mixed_colour'] += 1
            else:
                counts['whole_colour'] += 1

            unit = by_key[(script, offset)]
            target_runs = unit.get('runs')
            errors = []
            if mixed:
                if target_runs is None:
                    errors.append('missing target runs')
                else:
                    if len(target_runs) != len(source_runs):
                        errors.append('target/source run count differs')
                    if ''.join(target_runs) != unit.get('target', ''):
                        errors.append('target runs do not join into target')
            elif target_runs:
                errors.append('single-colour line has target runs')
            if errors:
                counts['structural_errors'] += 1
            else:
                counts['structurally_valid'] += 1
            if not coloured and not errors:
                continue

            rows = by_script[script]
            index = positions[(script, offset)]
            context = rows[max(0, index - 1):index + 2]
            records.append(dict(
                script=script,
                offset=offset,
                mode='mixed' if mixed else ('whole' if coloured else 'plain'),
                source_runs=source_runs,
                source=unit['source'],
                target=unit.get('target', ''),
                target_runs=target_runs,
                errors=errors,
                context=[dict(offset=row['offset'], source=row['source'],
                              target=row.get('target', '')) for row in context],
            ))
    return dict(schema=1, counts=counts, records=records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--output', default=str(WORK / 'reports/text-colour-audit.json'))
    args = parser.parse_args()
    report = audit()
    save(args.output, report)
    print(json.dumps(report['counts'], ensure_ascii=False))
    print('wrote ' + str(Path(args.output)))
    if args.strict and report['counts']['structural_errors']:
        raise SystemExit('%d colour-tag structural error(s)'
                         % report['counts']['structural_errors'])


if __name__ == '__main__':
    main()
