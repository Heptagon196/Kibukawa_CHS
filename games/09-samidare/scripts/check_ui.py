"""Check the ninth work's UI localization against the game's own label table.

The runtime answers UI text through ``Steezy.Localize.Localization::Get``, so every key
the game ships is a key a release has to answer: a missing one silently ships the
Japanese label. The game's ``en`` column is reference only and is never a source.

A key whose ``source`` no longer matches the shipped table is also a defect — the
runtime looks the row up by key, so the stored source is what documents which label the
translation belongs to, and a stale one hides a changed label.
"""
import csv
import io
import json
import sys
from pathlib import Path

import pipeline as p

UI = 'work/ui-localization.zh-CN.json'
LOCALIZATION = 'kibu9_Data/StreamingAssets/localization'


def table():
    """The shipped Key/ja/en rows, read from the verified original bundle."""
    assets = p.bundle_text_assets(LOCALIZATION)
    p.require('Localization' in assets, 'The localization bundle has no Localization table')
    rows = list(csv.DictReader(io.StringIO(assets['Localization'].decode('utf-8-sig'))))
    p.require(rows and 'Key' in rows[0] and 'ja' in rows[0], 'Unexpected localization table layout')
    return [dict(key=row['Key'], source=row['ja'], reference=row.get('en') or '') for row in rows]


def problems(rows, entries):
    """Every way the UI file and the shipped table can disagree."""
    found = []
    keyed = [entry for entry in entries if entry.get('key')]
    seen = set()
    for entry in keyed:
        if entry['key'] in seen:
            found.append('Duplicate localization key: ' + entry['key'])
        seen.add(entry['key'])
    shipped = {row['key']: row for row in rows}
    for key, row in shipped.items():
        entry = next((item for item in keyed if item['key'] == key), None)
        if entry is None:
            found.append('Missing localization key: ' + key)
            continue
        if entry.get('source') != row['source']:
            found.append('Source changed for %s: shipped %r, file %r'
                         % (key, row['source'], entry.get('source')))
        if not (entry.get('target') or '').strip():
            found.append('Empty translation for key: ' + key)
        elif row['source'].count('\n') != entry['target'].count('\n'):
            found.append('%s: the translation has a different number of line breaks' % key)
    for key in sorted(seen - set(shipped)):
        found.append('Key not in the shipped table: ' + key)
    if not any(not entry.get('key') for entry in entries):
        found.append('The UI file needs at least one literal entry without a key')
    return found


def run(path=None):
    """Return the list of problems for the release UI file (empty when it is sound)."""
    target = Path(path) if path else p.WORK / UI
    if not target.is_file():
        return ['Missing UI localization: ' + UI]
    document = json.loads(target.read_text(encoding='utf-8-sig'))
    entries = document.get('entries') if isinstance(document, dict) else document
    if not entries:
        return ['The UI localization file has no entries']
    return problems(table(), entries)


def main():
    found = run()
    rows = len(table())
    if found:
        print('UI localisation problems (%d) against %d shipped keys:' % (len(found), rows))
        for problem in found:
            print('   ' + problem)
        raise SystemExit(1)
    print('UI localisation OK: %d shipped keys all present, sources unchanged, translations non-empty' % rows)


if __name__ == '__main__':
    main()
