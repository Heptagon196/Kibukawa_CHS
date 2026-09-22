"""Audit production reflow counts, excluding proven fullscreen blocks."""
import csv
import json
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]

def main():
    source = json.loads((GAME/'research/source-replay.json').read_text(encoding='utf-8'))['scripts']
    by = {k.split('/')[-1]: (k, v) for k, v in source.items()}
    with (GAME/'reports/dialogue-page-rows.tsv').open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    keys = {(r['script'], int(r['offset'])) for r in rows}
    candidates = {(r['script'], int(r['offset'])) for r in rows if int(r['rows']) > int(r['capacity'])}
    excluded = []
    for name, offset in sorted(candidates):
        script, block = by[name]
        def mode_before(pos):
            return next(c for c in reversed(block['commands']) if c['offset'] < pos and c['name'] == 'MOJI_HANI')
        mode = mode_before(offset)
        assert mode['args'][0]['value'] == 2, (script, offset)
        labels = [x for x in block['labels'] if mode['offset'] < x <= offset]
        if labels:
            assert name == 'help', (script, offset, labels)
            # Help menu entries inherit fullscreen. All returns to that menu
            # also restore fullscreen before jumping; the illustrated ordinary
            # box section restores it at 2219 before its return.
            for c in block['commands']:
                if c['name'] in ('SENTAKUSI', 'TOBU'):
                    assert mode_before(c['offset'])['args'][0]['value'] == 2
                if c['name'] == 'TOBU':
                    assert c['args'][0]['value'] == 0
            assert block['labels'][0] == 51
        excluded.append(dict(script=script, offset=offset, mode_command=mode['offset'], mode=2,
            rows=max(int(r['rows']) for r in rows if r['script'] == name and int(r['offset']) == offset),
            proof='fullscreen help-menu entries and returns' if labels else 'fullscreen command without an intervening jump label'))
    report = dict(scope='Packaged dialogue, production Wrap, widths 204/220, capacities 4/5; fullscreen excluded',
        dialogue_blocks=len(keys), variants=len(rows), all_variants_within_four_rows=len(keys)-len(candidates),
        fullscreen_candidates=excluded, ordinary_overflow_count=0,
        limitation='Offline reflow and source context audit; no live game operation')
    (GAME/'reports/dialogue-page-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print({k:v for k,v in report.items() if k != 'fullscreen_candidates'})

if __name__ == '__main__':
    main()
