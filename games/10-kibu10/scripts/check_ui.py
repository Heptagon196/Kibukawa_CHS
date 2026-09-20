"""Read-only checks against the tenth game's shipped UI and audited IL inventory."""
import csv
import io
import re
import struct

import UnityPy
import pipeline as p
from generate_ui_data import ALLOWED, SENTINELS


def serialized_strings():
    root = p.GAME / 'kibu10_Data'
    files = [root / name for name in ('level0', 'resources.assets', 'sharedassets0.assets')]
    files += [f for f in (root / 'StreamingAssets/prefab').glob('*')
              if f.is_file() and f.suffix != '.manifest']
    found = []
    for file in files:
        for obj in UnityPy.load(str(file)).objects:
            if obj.type.name not in {'MonoBehaviour', 'TextAsset'}:
                continue
            raw = obj.get_raw_data()
            for offset in range(0, len(raw) - 4, 4):
                length = struct.unpack_from('<I', raw, offset)[0]
                if not 2 <= length <= 1024 or offset + 4 + length > len(raw):
                    continue
                try:
                    value = raw[offset + 4:offset + 4 + length].decode('utf-8')
                except UnicodeDecodeError:
                    continue
                if '\x00' in value or not re.search('[\u3040-\u30ff\u4e00-\u9fff\uff66-\uff9f]', value):
                    continue
                found.append(dict(asset_file=file.relative_to(p.GAME).as_posix(),
                                  path_id=obj.path_id, byte_offset=offset + 4, source_text=value))
    return found


def localization_rows():
    file = p.GAME / 'kibu10_Data/StreamingAssets/localization'
    for obj in UnityPy.load(str(file)).objects:
        if obj.type.name == 'TextAsset':
            data = obj.read()
            if data.m_Name == 'Localization':
                return list(csv.DictReader(io.StringIO(data.m_Script.lstrip('\ufeff'))))
    raise ValueError('Missing Localization TextAsset')


def key_problems(rows, entries):
    problems = []
    by_key = {e['key']: e for e in entries}
    if len(by_key) != len(entries):
        problems.append('Duplicate localization key')
    if set(by_key) != {r['Key'] for r in rows}:
        problems.append('Localization key coverage differs from shipped table')
    for row in rows:
        entry = by_key.get(row['Key'])
        if entry is None:
            continue
        if entry['source_text'] != row['ja']:
            problems.append('Source changed: ' + row['Key'])
        if not entry.get('target_text'):
            problems.append('Empty target: ' + row['Key'])
        elif entry['target_text'].count('\n') != row['ja'].count('\n'):
            problems.append('Line count differs: ' + row['Key'])
    return problems


def run():
    entries = p.load(p.WORK / 'work/ui-localization.zh-CN.json')['entries']
    errors = key_problems(localization_rows(), entries)
    assembly = p.load(p.WORK / 'work/ui-assembly.zh-CN.json')['entries']
    expected = [e for e in p.load(p.WORK / 'research/assembly-strings.json')
                if re.search('[\u3040-\u30ff\u4e00-\u9fff\uff66-\uff9f]', e['source_text'])
                or e['source_text'] in ('ON', 'OFF')]
    signature = lambda e: (e['token'], e['instruction'], e['method'], e['source_text'])
    if {signature(e) for e in expected} != {signature(e) for e in assembly}:
        errors.append('Assembly literal inventory differs')
    serialized = p.load(p.WORK / 'work/ui-serialized.zh-CN.json')['entries']
    signature = lambda e: (e['asset_file'], e['path_id'], e['byte_offset'], e['source_text'])
    if {signature(e) for e in serialized_strings()} != {signature(e) for e in serialized}:
        errors.append('Serialized UI inventory differs')
    exact = {}
    for entry in entries + assembly + serialized:
        if entry['classification'] not in ALLOWED:
            continue
        source, target = entry['source_text'], entry['target_text']
        if not target or source in SENTINELS:
            errors.append('Invalid UI target: ' + source)
            continue
        if re.search('[\u3040-\u30ff\uff66-\uff9f]', target):
            errors.append('Untranslated Japanese: ' + target)
        if sorted(re.findall(r'\{\d+\}', source)) != sorted(re.findall(r'\{\d+\}', target)):
            errors.append('Placeholder changed: ' + source)
        if source in exact and exact[source] != target:
            errors.append('Conflicting translation: ' + source)
        exact[source] = target
    # The two-line PaintMenu confirmations must retain their distinct destinations.
    if exact.get('タイトル画面に', '') + exact.get('戻ります。', '') != '即将返回标题画面。':
        errors.append('Title confirmation fragments do not join')
    if exact.get('シナリオ選択画面に', '') + exact.get('戻ります。', '') != '即将返回章节选择画面。':
        errors.append('Scenario confirmation fragments do not join')
    report = dict(schema=1, localize_keys=len(entries), assembly_literals=len(assembly),
                  serialized_occurrences=len(serialized), exact_strings=len(exact), errors=errors,
                  limitation='Offline source coverage only; in-game layout is user-validated.')
    p.save(p.WORK / 'reports/ui-check.json', report)
    if errors:
        raise ValueError('\n'.join(errors))
    print(report)
    return report


if __name__ == '__main__':
    run()
