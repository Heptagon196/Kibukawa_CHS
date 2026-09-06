"""Prepare independent translation batches and merge validated drafts atomically."""
import argparse
import collections
import json
import re
import time

import pipeline as p

DRAFTS = p.WORK/'work/drafts'
INPUTS = p.WORK/'work/batches'


def prepare():
    p.status()
    cache = p.load(p.WORK/'work/cache.json')
    groups = {}
    for group, data in cache['files'].items():
        batch = group[:-4] if re.fullmatch(r'scn\d+\.txt', group) else 'ui'
        for item in data['items']:
            if item['translation_status'] != 0:
                continue
            groups.setdefault(batch, []).append(dict(id=item['text_index'], source=item['source_text'],
                                                     group=group, location=item['extra']['location']))
    for name, rows in groups.items():
        path = INPUTS/(name+'.json')
        value = dict(batch=name, items=rows)
        if path.exists():
            p.require(p.load(path) == value, 'Existing batch differs; retain its source baseline: ' + name)
        else:
            p.save(path, value)
    DRAFTS.mkdir(parents=True, exist_ok=True)
    print({name: len(rows) for name, rows in groups.items()})


def check_draft(path, items):
    draft = p.load(path)
    baseline = p.load(INPUTS/(path.stem+'.json'))
    expected = {str(x['id']): x for x in baseline['items']}
    targets = draft['translations']
    p.require(set(targets) == set(expected), 'Missing or extra IDs in ' + path.name)
    empty_reasons = draft.get('empty_reasons', {})
    p.require(set(empty_reasons).issubset(targets), 'Unknown empty reason ID')
    for key, target in targets.items():
        source = expected[key]
        current = items[int(key)]
        p.require(current['source_text'] == source['source'], 'Source changed at ' + key)
        p.require(current['extra']['location'] == source['location'], 'Location changed at ' + key)
        p.require(isinstance(target, str) and '\0' not in target, 'Invalid target at ' + key)
        p.require(not any(0xd800 <= ord(c) <= 0xdfff for c in target), 'Unpaired surrogate at ' + key)
        if target == '':
            p.require(bool(empty_reasons.get(key)), 'Missing empty translation rationale at ' + key)
            # Only isolated name readings may be deliberately suppressed.
            p.require(bool(re.fullmatch(r'[\s()（）ｦ-ﾟァ-ヺぁ-ゖ・･ーｰ]+', source['source']))
                      and bool(re.search(r'[ｦ-ﾟァ-ヺぁ-ゖ]', source['source'])), 'Empty non-reading fragment at ' + key)
        else:
            p.require(bool(target.strip()) or target == source['source'], 'Changed whitespace-only target at ' + key)
        if source['location']['kind'] == 'script':
            p.require(not any(c in target for c in '\r\n\t'), 'Script control character at ' + key)
            p.require(len(target.encode('utf-16-le')) // 2 <= 20, 'Script target exceeds buffer at ' + key)
        tokens = lambda text: collections.Counter(re.findall(r'\{\d+(?:[^{}]*)\}|</?[A-Za-z][^>]*>', text))
        p.require(tokens(source['source']) == tokens(target), 'Placeholder/tag mismatch at ' + key)
        p.require(not re.search(r'[ぁ-ゖァ-ヺｦ-ﾟ]', target), 'Japanese kana remains at ' + key)
    return draft, expected


def merge():
    p.status()
    cache_path = p.WORK/'work/cache.json'
    original_bytes = cache_path.read_bytes()
    cache = json.loads(original_bytes)
    by_id = {x['text_index']: x for group in cache['files'].values() for x in group['items']}
    notes, empty, batches = [], {}, []
    for path in sorted(DRAFTS.glob('*.json')):
        draft, expected = check_draft(path, by_id)
        for key, target in draft['translations'].items():
            item = by_id[int(key)]
            p.require(item['translation_status'] in (0, 1), 'Cannot overwrite reviewed or excluded item ' + key)
            if item['translation_status'] == 1:
                p.require(item['translated_text'] == target, 'Draft conflicts with merged translation at ' + key)
            item.update(translated_text=target, translation_status=1, model='Codex')
            item['extra']['translation_batch'] = path.stem
        notes += [dict(batch=path.stem, note=n) for n in draft.get('notes', [])]
        empty.update(draft.get('empty_reasons', {}))
        batches.append(dict(batch=path.stem, count=len(expected), draft_sha256=p.sha(path.read_bytes())))
    p.require(batches, 'No translation drafts available')
    p.require(cache_path.read_bytes() == original_bytes, 'Cache changed concurrently; retry merge')
    backup = p.WORK/'work/backups'/('cache-before-translation-'+str(time.time_ns())+'.json')
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(original_bytes)
    pending = sum(x['translation_status'] == 0 for x in by_id.values())
    cache['extra']['translation_stage'] = 'first_draft_complete' if pending == 0 else 'draft_in_progress'
    p.save(cache_path, cache)
    p.save(p.WORK/'reports/translation-merge.json', dict(batches=batches, notes=notes, empty_name_readings=empty,
                                                       cache_sha256=p.sha(cache_path.read_bytes()), runtime_tested=False))
    for group, data in cache['files'].items():
        path = p.inside(p.WORK/'translated_texts'/group)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(f'[{x["text_index"]}] {x["translated_text"]}' for x in data['items']
                                   if x['translation_status'] in (1, 2)), encoding='utf-8', newline='')
    p.status()


def audit():
    p.status()
    cache_path = p.WORK/'work/cache.json'
    cache = p.load(cache_path)
    manifest = p.load(p.WORK/'work/manifest.json')
    rows = {x['text_index']: x for group in cache['files'].values() for x in group['items']}
    approved = {e['text_index'] for e in manifest['entries'] if not e['excluded']}
    seen = set()
    for path in sorted(DRAFTS.glob('*.json')):
        draft, expected = check_draft(path, rows)
        ids = {int(key) for key in expected}
        p.require(not seen.intersection(ids), 'Duplicate ID across batches')
        seen.update(ids)
        for key, target in draft['translations'].items():
            p.require(rows[int(key)]['translated_text'] == target, 'Draft/cache mismatch: ' + key)
    p.require(seen == approved, 'Draft coverage differs from all translatable entries')
    for entry in manifest['entries']:
        row = rows[entry['text_index']]
        p.require(row['extra']['location'] == entry['location'], 'Source location changed')
        if entry['excluded']:
            p.require(row['translation_status'] == 7 and row['translated_text'] == '', 'Excluded entry changed')
        else:
            p.require(row['translation_status'] == 1, 'Unexpected translation stage')
    for group, data in cache['files'].items():
        expected = '\n'.join(f'[{x["text_index"]}] {x["translated_text"]}' for x in data['items'] if x['translation_status'] in (1, 2))
        p.require((p.WORK/'translated_texts'/group).read_bytes() == expected.encode('utf-8'), 'Stale readable export: ' + group)
    before = p.load(p.WORK/'reports/translated-extract-before.json')
    # This historical regression snapshot predates later approved wording edits.
    # Source integrity is verified above; do not reject legitimate new drafts.
    reextract_snapshot_matches = all(p.sha((p.WORK/name).read_bytes()) == digest for name, digest in before.items())
    p.require(all((p.GAME/name).is_file() and p.sha((p.GAME/name).read_bytes()) == digest
                  for name, digest in manifest['game_hashes'].items()), 'Second-game original files changed')
    p.require(p.first_project_hashes() == p.load(p.WORK/'reports/first-project-baseline.json'), 'First-game files changed')
    report = dict(translated=len(approved), excluded=len(rows)-len(approved), batches=len(list(DRAFTS.glob('*.json'))),
                  max_script_utf16=max(len(x['translated_text'].encode('utf-16-le'))//2 for x in rows.values() if x['extra']['location']['kind'] == 'script'),
                  approved_empty_readings=[i for i in sorted(approved) if rows[i]['translated_text'] == ''],
                  all_sources_and_locations_preserved=True, all_readable_exports_current=True, original_game_unchanged=True,
                  first_project_unchanged=True, current_revision_matches_reextract_snapshot=reextract_snapshot_matches,
                  reextract_tested_cache_sha256=before.get('work/cache.json'),
                  cache_sha256=p.sha(cache_path.read_bytes()), runtime_tested=False,
                  release_ready=p.load(p.WORK/'project.json')['compatibility'].get('release_ready', False))
    p.save(p.WORK/'reports/translation-audit.json', report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'merge', 'audit'])
    args = parser.parse_args()
    globals()[args.action]()
