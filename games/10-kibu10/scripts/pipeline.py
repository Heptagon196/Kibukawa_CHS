"""Read-only tenth-game research extraction; never installs or launches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import UnityPy

WORK = Path(__file__).resolve().parents[1]
SERIES = WORK.parents[1]
sys.path.insert(0, str(SERIES / 'tools'))
from project_config import resolve
PROJECT = resolve(project=WORK, allow_disabled=True)
GAME = PROJECT['installation']
sys.path.insert(0, str(PROJECT['adapter_path']))
from vm import entries, parse_bin

def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def inside(path):
    path = Path(path).resolve()
    require(path.is_relative_to(WORK) and path != WORK, 'Output outside tenth-game project')
    return path


def save(path, data):
    path = inside(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def game_hashes():
    manifest = WORK / 'work/manifest.json'
    paths = load(manifest)['game_hashes'] if manifest.exists() else [p.relative_to(GAME).as_posix()
                                                                    for p in GAME.rglob('*') if p.is_file()]
    return {name: sha((GAME / name).read_bytes()) for name in sorted(paths)}


def first_project_hashes():
    """Protect preceding translation work, including existing untracked drafts."""
    return {p.relative_to(SERIES).as_posix(): sha(p.read_bytes())
            for directory in sorted((SERIES / 'games').iterdir()) if directory != WORK and directory.is_dir()
            for p in (directory / 'work').rglob('*') if p.is_file()}


def validate_sources():
    manifest = load(WORK / 'work/manifest.json')
    for name, digest in manifest['source_hashes'].items():
        require(sha((GAME / name).read_bytes()) == digest, 'Original changed: ' + name)
    return manifest


def shell():
    """The PowerShell interpreter to shell out to.

    PowerShell 7 is not always on PATH even when it is installed; ``run.ps1`` falls
    back to the interpreter recorded in ``runtime.json``, and the build scripts have to
    resolve it the same way rather than assuming ``pwsh`` resolves on its own.
    """
    found = shutil.which('pwsh')
    if found:
        return found
    record = SERIES / 'runtime.json'
    if record.is_file():
        candidate = load(record).get('pwsh')
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError('PowerShell 7 not found: install it or point runtime.json at it')


def inspect(game, data, output):
    inside(output).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([shell(), '-NoProfile', '-File', str(WORK / 'scripts/inspect_assembly.ps1'),
                    '-InputDll', str(game / data / 'Managed/Assembly-CSharp.dll'), '-OutputJson', str(output)], check=True)
    return load(output)


def bundle_text_assets(relative):
    assets = {}
    for obj in UnityPy.load(str(GAME / relative)).objects:
        if obj.type.name == 'TextAsset':
            asset = obj.read()
            require(asset.m_Name not in assets, 'Duplicate TextAsset')
            assets[asset.m_Name] = asset.m_Script.encode('utf-8', 'surrogateescape')
    return assets


def normalized_methods(data, prefix):
    return {re.sub(r'(?<=d__)\d+', '#', key.replace(prefix, '')):
            re.sub(r'(?<=d__)\d+', '#', '\n'.join(value['body']).replace(prefix, ''))
            for key, value in data['methods'].items() if 'CanvasEx' in key}


def row_markup(row):
    import html
    result, text, color = [], '', None
    def flush():
        nonlocal text
        if text:
            result.append('<color=' + str(color) + '>' + html.escape(text, quote=False) + '</color>')
            text = ''
    for i, cell in enumerate(row['cells']):
        next_color = row['colors'][i]
        if color != next_color:
            flush()
            color = next_color
        text += cell.replace('\uf8f3', '')
        control = row['controls'][i] if row['controls'] else 0
        if control:
            flush()
            result.append('<ctrl=' + format(control, '02X') + '/>')
    flush()
    return ''.join(result)


def extract():
    import base64
    import html
    import struct
    existing = (WORK / 'work/manifest.json').exists()
    if existing:
        validate_sources()
    before, prior = game_hashes(), first_project_hashes()
    save(WORK / 'reports/previous-translations-baseline.json', prior)
    target = inspect(GAME, 'kibu10_Data', WORK / 'research/kibu10-assembly.json')
    baseline_config = resolve('kibu8', allow_disabled=True)
    baseline = inspect(baseline_config['installation'], 'kibu8_Data', WORK / 'research/kibu8-assembly.json')
    expected = load(baseline_config['project'] / 'work/manifest.json')['source_hashes']
    require(baseline['assembly_sha256'] == expected['kibu8_Data/Managed/Assembly-CSharp.dll'], 'Unverified eighth-game baseline')
    old, new = normalized_methods(baseline, 'appli1.'), normalized_methods(target, '')
    common = old.keys() & new.keys()
    comparison = dict(baseline='kibu8', baseline_sha256=baseline['assembly_sha256'],
        target_sha256=target['assembly_sha256'], unchanged_methods=sorted(k for k in common if old[k] == new[k]),
        changed_methods=sorted(k for k in common if old[k] != new[k]),
        missing_methods=sorted(old.keys() - new.keys()), added_methods=sorted(new.keys() - old.keys()),
        codec_equal=baseline['codec_base64'] == target['codec_base64'], runtime_tested=False,
        conclusion='Eighth-game 20050817 row planes reused. Direct-bin container, ordinary Game_adv, '
                   'KOMANDO/HAIKEI_SETTI operands and SABUTAITORU/SINARIOSENTAKU differ. Thin variant required.')
    save(WORK / 'research/engine-comparison.json', comparison)
    save(WORK / 'research/assembly-strings.json', target['strings'])
    codec = struct.unpack('<65537H', base64.b64decode(target['codec_base64']))
    scratch = bundle_text_assets('kibu10_Data/StreamingAssets/scratchpad')
    files = bundle_text_assets('kibu10_Data/StreamingAssets/file')
    scripts = [('scratch4.dat', n, r) for n, r in entries(scratch['scratch4.dat'])]
    scripts += [('file', n, r) for n, r in files.items() if n.endswith('.bin')]
    previous_path = WORK / 'work/dialogue-tagged.json'
    previous = {u['id']: u for u in load(previous_path)['units']} if previous_path.exists() else {}
    units, records, replay, inventory = [], [], {}, []
    for container, name, raw in scripts:
        require(name.endswith('.bin'), 'Unexpected non-scenario in scratch4')
        path = inside(WORK / 'raw' / container / name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        script = container + '/' + Path(name).stem
        parsed = parse_bin(raw, codec)
        replay[script] = parsed
        active = container == 'file' or name not in ('start.bin', 'define.bin', 'append.bin', 'help.bin')
        inventory.append(dict(script=script, bytes=len(raw), sha256=sha(raw), commands=len(parsed['commands']), active=active))
        candidates = []
        for c in parsed['commands']:
            op = c['opcode']
            if c['rows']:
                source = '<row/>'.join(row_markup(row) for row in c['rows'])
                if re.sub('<[^>]*>', '', source).strip():
                    candidates.append(dict(id=script + ':' + str(c['offset']), script=script,
                        instruction=c['offset'], end=c['end'], opcode=op,
                        kind='dialogue' if op == 255 else 'display', source=source))
            for index, arg in enumerate(c['args']):
                if (op == 8 and index == 0 or op in (17, 73) and index == 1) and arg['value'].strip():
                    candidates.append(dict(id=script + ':' + str(c['offset']) + ':arg' + str(index),
                        script=script, instruction=c['offset'], end=c['end'], opcode=op, argument=index,
                        kind={8:'choice', 17:'name', 73:'subtitle'}[op], source=html.escape(arg['value'], quote=False)))
        for unit in candidates:
            prior_unit = previous.get(unit['id'])
            require(prior_unit is None or prior_unit['source'] == unit['source'], 'Source changed: ' + unit['id'])
            unit.update(active=active, target=prior_unit.get('target', '') if prior_unit else '',
                        translation_status=prior_unit.get('translation_status', 'pending') if prior_unit else 'pending')
            units.append(unit)
            records.append(dict(text_index=len(records)+1, source_text=html.unescape(re.sub('<[^>]*>', '', unit['source'])),
                tagged_source=unit['source'], group=script+'.txt', excluded=not active,
                location=dict(kind='script', file='kibu10_Data/StreamingAssets/'+('file' if container=='file' else 'scratchpad'),
                    asset=name if container=='file' else container, member=name,
                    instruction=unit['instruction'], opcode=unit['opcode'], unit_id=unit['id'], argument=unit.get('argument', 0))))
    require(not (previous.keys() - {u['id'] for u in units}), 'Existing draft entries disappeared')
    source_names = ['kibu10_Data/Managed/Assembly-CSharp.dll'] + ['kibu10_Data/StreamingAssets/'+x for x in ('scratchpad','file','localization')]
    source_hashes = {n: before[n] for n in source_names}
    for n in source_names:
        path = inside(WORK / 'originals' / n)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((GAME / n).read_bytes())
    save(WORK / 'work/manifest.json', dict(version=1, source_hashes=source_hashes, game_hashes=before, entries=records,
        coverage='Scenario rows, choices, names and subtitles; shell UI/images still pending'))
    document = dict(schema=2, adapter=PROJECT['adapter'], units=units)
    save(previous_path, document)
    save(WORK / 'texts/dialogue-tagged.json', document)
    save(WORK / 'research/source-replay.json', dict(schema=2, scripts=replay))
    save(WORK / 'research/container-inventory.json', inventory)
    cache_path = WORK / 'work/cache.json'
    if not cache_path.exists():
        save(cache_path, dict(project_id='kibu10-'+source_hashes[source_names[1]][:16], project_type='Txt',
            project_name=PROJECT['title'], input_path=os.path.relpath(GAME, SERIES).replace('\\', '/'),
            files={}, stats_data={}, extra=dict(translation_stage='source_extracted', authoritative_draft='work/dialogue-tagged.json',
            note='Cache initialization only; reviewed write-back is not implemented.')))
    require(before == game_hashes(), 'Game changed during extraction')
    after = first_project_hashes()
    changes = sorted(n for n in prior.keys() | after.keys() if prior.get(n) != after.get(n))
    save(WORK / 'reports/extraction.json', dict(scenarios=len(scripts), commands=sum(i['commands'] for i in inventory),
        text_units=len(units), active_text_units=sum(u['active'] for u in units), translated=sum(bool(u['target']) for u in units),
        script_extraction_complete=True, text_extraction_complete=False,
        original_game_unchanged=True, previous_translation_work_unchanged=not changes,
        concurrent_previous_translation_changes=changes, runtime_tested=False))
    status()


def status():
    if not (WORK / 'work/manifest.json').exists():
        print('kibu10 registered; extraction pending; release disabled.')
        return
    validate_sources()
    print(json.dumps(dict(game='kibu10', **load(WORK / 'reports/extraction.json')), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['extract', 'status'])
    globals()[parser.parse_args().action]()
