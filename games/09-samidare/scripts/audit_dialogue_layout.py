"""Record every token split rather than equating width checks with linguistic QA."""
import argparse
import json
from pathlib import Path


def audit(folder):
    report = json.loads((folder / 'dialogue-layout.json').read_text(encoding='utf-8'))
    split, widows = [], []
    for e in report['examples']:
        n, cuts = 0, set()
        for row in e['after'][:-1]:
            n += len(row)
            cuts.add(n)
        n = 0
        for token in e['tokens']:
            if cuts.intersection(range(n + 1, n + len(token))):
                split.append(dict(script=e['script'], offset=e['offsets'][0],
                                  token=token, rows=e['after'], width=e['block_width']))
            n += len(token)
        if (len(e['after']) > 1
                and len(e['after'][-1].strip('，。！？…')) < 2
                and e['after'][-1] != e['before'][-1]):
            widows.append(e)
    result = dict(groups=report['groups'], token_splits=split, single_character_last_rows=widows,
                  manual_gameplay_verified=False)
    (folder / 'segmentation-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    audit(parser.parse_args().folder)
