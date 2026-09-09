"""Read-only kibu3 extraction. Writes are confined to this game's project.

No imports from the first game's pipeline; no patch/install/launch operations.
"""
import argparse
import base64
import collections
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time
import zipfile

import UnityPy

WORK = Path(__file__).resolve().parents[1]
SERIES = WORK.parents[1]
sys.path.insert(0, str(SERIES / 'tools'))
from project_config import resolve
PROJECT = resolve(project=WORK, allow_disabled=True)
GAME = PROJECT['installation']
DATA = 'kibu3_Data/'
STREAM = DATA + 'StreamingAssets/'
DLL = DATA + 'Managed/Assembly-CSharp.dll'
JP = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]')


def require(test, message):
    if not test:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def inside(path):
    result = Path(path).resolve()
    require(result.is_relative_to(WORK) and result != WORK, 'Output outside third-game project: ' + str(result))
    return result


def save(path, data):
    path = inside(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def game_hashes():
    return {p.relative_to(GAME).as_posix(): sha(p.read_bytes())
            for p in sorted(GAME.rglob('*')) if p.is_file()}


def first_project_hashes():
    # Protect every file in both preceding projects, including untracked edits.
    return {f.relative_to(SERIES).as_posix(): sha(f.read_bytes())
            for name in ('01-kamen-gensou', '02-kairou')
            for f in (SERIES/'games'/name).rglob('*') if f.is_file()}



def raw(obj):
    return obj.read().m_Script.encode('utf-8', 'surrogateescape')


def text_assets(path):
    result = {}
    for obj in UnityPy.load(str(path)).objects:
        if obj.type.name == 'TextAsset':
            name = obj.read().m_Name
            require(name not in result, 'Duplicate TextAsset: ' + name)
            result[name] = raw(obj)
    return result


def definitions(data):
    result = {}
    pos = 1
    for _ in range(data[0]):
        size = data[pos]
        pos += 1
        require(size >= 1 and pos + size <= len(data), 'Truncated command definition')
        opcode = data[pos]
        require(opcode not in result, 'Duplicate opcode')
        result[opcode] = list(data[pos+1:pos+size])
        pos += size
    require(pos == len(data), 'Trailing command-definition bytes')
    return result


def decode(data, table):
    result = []
    pos = 0
    while pos < len(data):
        char = data[pos]
        pos += 1
        if 0x81 <= char <= 0x9f or 0xe0 <= char <= 0xea:
            require(pos < len(data), 'Truncated SJIS character')
            char = (char << 8) | data[pos]
            pos += 1
        require(table[char] != 0, 'Unmapped SJIS character: ' + hex(char))
        result.append(chr(table[char]))
    return ''.join(result)


def parse_script(data, defs):
    pos = 0
    commands = []
    while pos < len(data):
        start = pos
        opcode = data[pos]
        pos += 1
        require(opcode in defs, f'Unknown opcode {opcode} at {start}')
        args = []
        for kind in defs[opcode]:
            begin = pos
            if kind == 3:
                pos = data.index(0, pos) + 1
                value = data[begin:pos-1]
            else:
                require(kind in (0, 1, 2, 4, 5), 'Unknown argument type')
                pos += {0: 1, 1: 2, 2: 4, 4: 2, 5: 1}[kind]
                require(pos <= len(data), 'Truncated argument')
                value = int.from_bytes(data[begin:pos], 'big')
            args.append(dict(kind=kind, offset=begin, end=pos, value=value))
        commands.append(dict(offset=start, end=pos, opcode=opcode, args=args))
    boundaries = {c['offset'] for c in commands}
    for command in commands:
        for arg in command['args']:
            if arg['kind'] == 4:
                require(arg['value'] == 65535 or arg['value'] in boundaries, 'Invalid script jump target')
    return commands


def sub_parts(data):
    pos = 1
    result = []
    for _ in range(data[0]):
        require(pos + 2 <= len(data), 'Truncated subscenario header')
        size = int.from_bytes(data[pos:pos+2], 'big')
        pos += 2
        require(pos + size <= len(data), 'Truncated subscenario')
        result.append(data[pos:pos+size])
        pos += size
    require(pos == len(data), 'Trailing subscenario bytes')
    return result


def aligned_strings(data):
    occupied = 0
    for offset in range(0, len(data)-4, 4):
        if offset < occupied:
            continue
        size = struct.unpack_from('<i', data, offset)[0]
        if not 1 <= size <= len(data)-offset-4:
            continue
        end = (offset+4+size+3) & ~3
        if end > len(data) or any(data[offset+4+size:end]):
            continue
        try:
            value = data[offset+4:offset+4+size].decode('utf-8')
        except UnicodeError:
            continue
        if not JP.search(value) or any(ord(c) < 32 and c not in '\r\n\t' for c in value):
            continue
        occupied = end
        yield offset, end, value


def inspect(game, data_dir, destination):
    destination = inside(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['pwsh', '-NoProfile', '-File', str(WORK/'scripts/inspect_assembly.ps1'),
                    '-InputDll', str(game/data_dir/'Managed/Assembly-CSharp.dll'),
                    '-OutputJson', str(destination)], check=True)
    return load(destination)


def validate_sources():
    manifest = load(WORK/'work/manifest.json')
    for rel, digest in manifest['source_hashes'].items():
        require(sha((GAME/rel).read_bytes()) == digest, 'Original game changed: ' + rel)
    return manifest


def extract():
    manifest_path = WORK/'work/manifest.json'
    existing = None
    cache_hash = None
    if manifest_path.exists():
        existing = validate_sources()
        require((WORK/'work/cache.json').is_file(), 'Existing manifest has no cache; restore it from backup')
        status()
        cache_hash = sha((WORK/'work/cache.json').read_bytes())
    else:
        require(not (WORK/'work/cache.json').exists(), 'Cache already exists without manifest; refusing to overwrite')
    before = game_hashes()
    first_before = first_project_hashes()
    second = inspect(GAME, DATA, WORK/'research/kibu3-assembly.json')
    first_config = resolve('kibu1')
    first = inspect(first_config['installation'], 'kibu1_Data', WORK/'research/kibu1-assembly.json')
    # Compare against the approved baseline rather than a possibly patched DLL.
    first_manifest = load(first_config['project']/'work/manifest.json')
    require(first['assembly_sha256'] == first_manifest['source_hashes']['kibu1_Data/Managed/Assembly-CSharp.dll'], 'First-game reference differs from approved original')
    prior_config = resolve('kibu2')
    prior = inspect(prior_config['installation'], 'kibu2_Data', WORK/'research/kibu2-assembly.json')
    prior_manifest = load(prior_config['project']/'work/manifest.json')
    require(prior['assembly_sha256'] == prior_manifest['source_hashes']['kibu2_Data/Managed/Assembly-CSharp.dll'], 'Second-game reference differs from approved original')
    table = struct.unpack('<65537H', base64.b64decode(second['codec_base64']))
    file_assets = text_assets(GAME/(STREAM+'file'))
    defs = definitions(file_assets['define'])
    first_assets = text_assets(first_config['installation']/'kibu1_Data/StreamingAssets/file')
    archive_name = load(WORK/'project.json')['resource_archive']
    archive = zipfile.ZipFile(io.BytesIO(text_assets(GAME/(STREAM+'scratchpad'))[archive_name]))
    require(archive.testzip() is None, 'Corrupt original scenario archive')
    entries, files, sources, script_stats, replay = [], {}, {}, {}, []

    def snapshot(rel):
        if rel not in sources:
            data = (GAME/rel).read_bytes()
            require(sha(data) == before[rel], 'Source changed during extraction')
            sources[rel] = sha(data)
            path = inside(WORK/'originals'/rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def add(group, value, location, excluded=False, note=''):
        if not value:
            return
        snapshot(location['file'])
        index = len(entries) + 1
        entries.append(dict(text_index=index, source_text=value, location=location, group=group, excluded=excluded, reason=note))
        item = dict(text_index=index, source_text=value, translated_text='', translation_status=7 if excluded else 0,
                    model='', text_to_detect=value, extra=dict(location=location, note=note))
        files.setdefault(group, dict(storage_path=group, encoding='utf-8', file_project_type='Txt', line_ending='\n', items=[], extra={}))['items'].append(item)

    scripts = [(name, archive.read(name), dict(file=STREAM+'scratchpad', asset=archive_name, member=name))
               for name in sorted(archive.namelist(), key=lambda n: int(n[3:]) if re.fullmatch(r'scn\d+', n) else -1)
               if re.fullmatch(r'scn\d+', name)]
    scripts += [(f'subscn_{i+1}', data, dict(file=STREAM+'file', asset='subscn', part=i))
                for i, data in enumerate(sub_parts(file_assets['subscn']))]
    require(scripts, 'No scenarios found')
    for name, data, location in scripts:
        commands = parse_script(data, defs)
        strings = 0
        for command in commands:
            decoded = []
            for index, arg in enumerate(command['args']):
                if arg['kind'] != 3:
                    continue
                value = decode(arg['value'], table)
                decoded.append(value if arg['value'] else None)
                strings += bool(value)
                add(name+'.txt', value, dict(location, kind='script', offset=arg['offset'], instruction=command['offset'], opcode=command['opcode'], argument=index))
            replay.append(dict(script=name, instruction=command['offset'], opcode=command['opcode'], nextCursor=command['end'], strings=decoded, integers=[a['value'] if a['value']<2147483648 else a['value']-4294967296 for a in command['args'] if a['kind']!=3]))
        script_stats[name] = dict(bytes=len(data), instructions=len(commands), strings=strings,
                                 jumps=sum(arg['kind'] == 4 for c in commands for arg in c['args']))
    rows = list(csv.reader(io.StringIO(text_assets(GAME/(STREAM+'localization'))['Localization'].decode('utf-8-sig'))))
    ja = rows[0].index('ja')
    for index, row in enumerate(rows[1:], 1):
        require(len(row) > ja, 'Truncated localization row')
        add('localization_ja.csv', row[ja], dict(kind='csv', file=STREAM+'localization', asset='Localization', row=index, column=ja, key=row[0]))
    paths = list((GAME/STREAM).rglob('*')) + list((GAME/DATA).glob('*.assets')) + [GAME/DATA/'level0']
    for path in sorted(paths):
        if not path.is_file() or path.suffix == '.manifest':
            continue
        rel = path.relative_to(GAME).as_posix()
        for obj in sorted(UnityPy.load(str(path)).objects, key=lambda o: o.path_id):
            if obj.type.name != 'MonoBehaviour':
                continue
            for offset, end, value in aligned_strings(obj.get_raw_data()):
                excluded = offset == 28 or bool(re.search(r'説明１６字|ボタン名|１プライヤー名|ランキング名', value))
                add('ui/'+rel+'.txt', value, dict(kind='unity_string', file=rel, asset_file=obj.assets_file.name, path_id=obj.path_id, offset=offset, end=end),
                    excluded, 'Template/identifier candidate' if excluded else 'Serialized UI candidate; review context before translating')
    for entry in second['strings']:
        value, method = entry['source_text'], entry['method']
        if not JP.search(value):
            continue
        visible = any(name in method for name in ('CanvasEx', 'CharacterInputDialog', 'CharacterInputKeyManager::Init', 'WindowDialog'))
        add('assembly_ui.txt' if visible else 'excluded/assembly_technical.txt', value,
            dict(kind='assembly', file=DLL, token=entry['token'], instruction=entry['instruction'], method=method),
            not visible, 'UI literal candidate' if visible else 'Technical literal; excluded pending review')
    for rel in (DLL, STREAM+'file', STREAM+'scratchpad', STREAM+'localization'):
        snapshot(rel)
    changed = [name for name, method in first['methods'].items() if method['sha256'] != second['methods'].get(name, {}).get('sha256')]
    comparisons = dict(first_assembly_sha256=first['assembly_sha256'], target_assembly_sha256=second['assembly_sha256'],
                       first_methods=len(first['methods']), target_methods=len(second['methods']), changed_methods=changed,
                       added_methods=sorted(set(second['methods'])-set(first['methods'])),
                       fields_equal=first['fields'] == second['fields'], codec_equal=first['codec_base64'] == second['codec_base64'],
                       definitions_equal=file_assets['define'] == first_assets['define'],
                       archive=archive_name, archive_members=archive.namelist(), game_runtime_tested=False,
                       note='Normalized method bodies and field metadata only; asset/layout compatibility still needs review.')
    comparisons['versus_kibu2'] = dict(assembly_sha256=prior['assembly_sha256'],
        changed_methods=[n for n,m in prior['methods'].items() if m['sha256'] != second['methods'].get(n, {}).get('sha256')],
        added_methods=sorted(set(second['methods'])-set(prior['methods'])),
        fields_equal=prior['fields']==second['fields'], codec_equal=prior['codec_base64']==second['codec_base64'],
        definitions_equal=file_assets['define']==text_assets(prior_config['installation']/'kibu2_Data/StreamingAssets/file')['define'])
    cache = dict(project_id='kibu3-'+sources[STREAM+'scratchpad'][:16], project_type='Txt', project_name=PROJECT['title'],
                 project_create_time=time.strftime('%Y-%m-%d %H:%M:%S'), input_path=os.path.relpath(GAME, SERIES).replace('\\', '/'),
                 stats_data={}, files=files, detected_encoding='utf-8', detected_line_ending='\n',
                 extra=dict(format='socotra-unity-v1', translation_stage='not_started'))
    require(game_hashes() == before, 'Third-game files changed during extraction')
    require(first_project_hashes() == first_before, 'Previous-game project files changed during extraction')
    manifest = dict(version=1, source_hashes=sources, game_hashes=before, entries=entries, script_stats=script_stats,
                    codec_base64=second['codec_base64'], definitions=defs)
    if existing is None:
        save(WORK/'work/cache.json', cache)
        save(manifest_path, manifest)
    else:
        # JSON normalizes integer opcode keys to strings. Refuse a changed
        # extractor mapping; existing translation indexes must remain stable.
        normalized = json.loads(json.dumps(manifest))
        for key in ('source_hashes', 'entries', 'script_stats', 'codec_base64', 'definitions'):
            require(existing[key] == normalized[key], 'Extraction mapping changed; review migration before replacing: ' + key)
        require(sha((WORK/'work/cache.json').read_bytes()) == cache_hash, 'Translation cache changed during extraction')
    save(WORK/'research/engine-comparison.json', comparisons)
    save(WORK/'research/source-replay.json', dict(commands=replay))
    from dialogue_tags import document
    save(WORK/'texts/dialogue-tagged.json',document(WORK,replay))
    save(WORK/'reports/previous-projects-extract-baseline.json', first_before)
    for name, group in files.items():
        path = inside(WORK/'texts'/name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(f'[{x["text_index"]}] {x["source_text"]}' for x in group['items']), encoding='utf-8')
    report = dict(total=len(entries), translatable=sum(not e['excluded'] for e in entries), excluded=sum(e['excluded'] for e in entries),
                  scripts=script_stats, original_game_unchanged=True, previous_projects_unchanged=True,
                  coverage='All scn members, subscn parts, localization ja, aligned CJK MonoBehaviour strings and managed ldstr. Images and native binaries need separate review.',
                  compatibility=comparisons)
    save(WORK/'reports/extraction.json', report)
    if existing is not None:
        require(sha((WORK/'work/cache.json').read_bytes()) == cache_hash, 'Translation cache changed during extraction')
        print('Derived snapshots, texts and research rebuilt; existing cache and manifest preserved byte-for-byte.')
    status()


def status():
    if not (WORK/'work/cache.json').exists():
        print('kibu3 registered; extraction pending, release disabled.')
        return
    manifest = validate_sources()
    cache = load(WORK/'work/cache.json')
    items = [item for group in cache['files'].values() for item in group['items']]
    by_id = {x['text_index']: x for x in items}
    require(len(by_id) == len(items) == len(manifest['entries']), 'Missing or duplicate cache entries')
    for source in manifest['entries']:
        require(by_id[source['text_index']]['source_text'] == source['source_text'], 'Original cache text changed')
    compatibility = load(WORK/'project.json')['compatibility']
    print(json.dumps(dict(game='kibu3', total=len(items), statuses=dict(collections.Counter(x['translation_status'] for x in items)),
                          source_hashes_verified=True, release_ready=compatibility.get('release_ready', False),
                          runtime_tested=compatibility.get('runtime_tested', False)), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['extract', 'status'])
    args = parser.parse_args()
    globals()[args.action]()
