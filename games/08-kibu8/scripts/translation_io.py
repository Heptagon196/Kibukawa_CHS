"""Eighth-game draft storage and structural checks; never approves semantic review."""
import hashlib
import html
import json
from pathlib import Path
import re

WORK = Path(__file__).resolve().parents[1]
TAG = re.compile(r'<[^>]+>')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path).resolve()
    if not path.is_relative_to(WORK):
        raise ValueError('Writes must stay within eighth-game project')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def plain(value):
    return html.unescape(TAG.sub('', value))


def check_target(source, target):
    if not isinstance(target, str):
        raise ValueError('Target must be a string')
    if TAG.findall(source) != TAG.findall(target):
        raise ValueError('Color/control/row tags changed')
    if any(char in target for char in '\r\n\t\0'):
        raise ValueError('Unexpected literal whitespace/control character')
    for text in TAG.split(target):
        if '<' in text or '>' in text:
            raise ValueError('Escape literal angle brackets as entities')


def merge_batches(document, paths):
    """Exact source matching prevents applying stale or duplicate agent results."""
    units = {unit['id']: unit for unit in document['units']}
    if len(units) != len(document['units']):
        raise ValueError('Duplicate authoritative IDs')
    seen = set()
    for path in paths:
        batch = load(path)
        for translated in batch['units']:
            key = translated['id']
            if key in seen or key not in units:
                raise ValueError('Duplicate/unknown batch ID: ' + key)
            seen.add(key)
            original = units[key]
            if translated['source'] != original['source']:
                raise ValueError('Source changed: ' + key)
            check_target(original['source'], translated['target'])
            if not plain(translated['target']).strip() and plain(original['source']).strip():
                raise ValueError('Untranslated text: ' + key)
            original['target'] = translated['target']
            original['translation_status'] = 'draft'
            original['translation_notes'] = translated.get('notes', '')
    return len(seen)
